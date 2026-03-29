"""Module 3: Extractor — parse HTML into candidate items."""

from __future__ import annotations

import json
import logging
import re

from bs4 import BeautifulSoup, Tag

from feed_extractor.models import CandidateItem, FetchResult

logger = logging.getLogger(__name__)

# Patterns to detect item types
PROMO_KEYWORDS = re.compile(
    r"(promoci[oó]n|descuento|oferta|cupón|cupon|rebaja|2x1|%\s*off|% de descuento|gratis|sale)",
    re.IGNORECASE,
)
EVENT_KEYWORDS = re.compile(
    r"(evento|concierto|exposici[oó]n|taller|festival|inauguraci[oó]n|clase|show|función|funcion|presentaci[oó]n)",
    re.IGNORECASE,
)


def _classify_type(text: str) -> str:
    """Classify item type based on keyword presence."""
    if PROMO_KEYWORDS.search(text):
        return "promo"
    if EVENT_KEYWORDS.search(text):
        return "event"
    return "event"  # default


def _extract_price_text(text: str) -> str:
    """Try to extract price or discount mentions from text."""
    patterns = [
        r"\$[\d,]+(?:\.\d{2})?",  # $1,234.00
        r"\d+%\s*(?:de\s+)?(?:descuento|off)",  # 20% descuento
        r"2x1|3x2",
        r"gratis",
    ]
    matches = []
    for pattern in patterns:
        matches.extend(re.findall(pattern, text, re.IGNORECASE))
    return "; ".join(matches) if matches else ""


def _extract_date_text(text: str) -> str:
    """Try to extract date-like strings from text."""
    patterns = [
        r"\d{1,2}\s+de\s+\w+(?:\s+de\s+\d{4})?",  # 15 de marzo de 2026
        r"del?\s+\d{1,2}\s+al\s+\d{1,2}\s+de\s+\w+",  # del 15 al 30 de marzo
        r"hasta\s+(?:el\s+)?\d{1,2}\s+de\s+\w+",  # hasta el 30 de marzo
        r"vigente\s+hasta\s+\w+",  # vigente hasta abril
        r"\d{1,2}/\d{1,2}/\d{2,4}",  # 15/03/2026
        r"\d{4}-\d{2}-\d{2}",  # 2026-03-15
    ]
    matches = []
    for pattern in patterns:
        matches.extend(re.findall(pattern, text, re.IGNORECASE))
    return "; ".join(matches) if matches else ""


def _clean_text(text: str) -> str:
    """Collapse whitespace and strip."""
    return re.sub(r"\s+", " ", text).strip()


def extract_items_generic(fetch_result: FetchResult) -> list[CandidateItem]:
    """Generic extraction: find article/card-like elements in HTML.

    This is a broad heuristic extractor. Per-source custom extractors
    can be added later for higher precision.
    """
    if not fetch_result.ok or not fetch_result.content:
        return []

    soup = BeautifulSoup(fetch_result.content, "lxml")
    items: list[CandidateItem] = []

    # Look for common card/article patterns
    selectors = [
        "article",
        "[class*='card']",
        "[class*='event']",
        "[class*='promo']",
        "[class*='item']",
        ".post",
        ".entry",
    ]

    seen_titles: set[str] = set()
    elements: list[Tag] = []

    for selector in selectors:
        elements.extend(soup.select(selector))

    # Fallback: if nothing found, try all divs with headings inside
    if not elements:
        for div in soup.find_all("div"):
            if div.find(["h1", "h2", "h3", "h4"]):
                elements.append(div)

    for el in elements:
        # Extract title from heading or first strong text
        heading = el.find(["h1", "h2", "h3", "h4", "h5"])
        title = _clean_text(heading.get_text()) if heading else ""

        if not title:
            strong = el.find("strong")
            if strong:
                title = _clean_text(strong.get_text())

        if not title or len(title) < 5:
            continue

        # Skip duplicates within same page
        title_key = title.lower()
        if title_key in seen_titles:
            continue
        seen_titles.add(title_key)

        full_text = _clean_text(el.get_text())
        description = full_text[:500] if len(full_text) > 500 else full_text

        # Extract image
        img = el.find("img")
        image_url = ""
        if img:
            image_url = img.get("src", "") or img.get("data-src", "")

        # Extract link
        link = el.find("a", href=True)
        detail_url = link["href"] if link else ""

        item = CandidateItem(
            title=title,
            description=description,
            item_type=_classify_type(full_text),
            business_name=fetch_result.source.name,
            venue_name=fetch_result.source.name,
            raw_location=_extract_location_text(full_text),
            raw_date=_extract_date_text(full_text),
            raw_price=_extract_price_text(full_text),
            source_url=detail_url or fetch_result.url,
            source_name=fetch_result.source.name,
            image_url=image_url,
            raw_extracted={
                "full_text": full_text[:1000],
                "html": str(el)[:2000],
            },
        )
        items.append(item)

    logger.info(
        "Extracted %d items from %s", len(items), fetch_result.source.name
    )
    return items


def _extract_location_text(text: str) -> str:
    """Try to extract location-related text."""
    patterns = [
        r"(?:ubicaci[oó]n|direcci[oó]n|lugar|sede|en)\s*:?\s*([^.;\n]{10,80})",
        r"(?:Av\.|Calle|Blvd\.|Calzada)[^.;\n]{5,80}",
    ]
    matches = []
    for pattern in patterns:
        found = re.findall(pattern, text, re.IGNORECASE)
        matches.extend(found)
    return "; ".join(matches[:3]) if matches else ""


def extract_items_eventbrite(fetch_result: FetchResult) -> list[CandidateItem]:
    """Extract events from Eventbrite search results page.

    Parses the window.__SERVER_DATA__ JSON and JSON-LD structured data.
    """
    if not fetch_result.ok or not fetch_result.content:
        return []

    items: list[CandidateItem] = []

    # Primary: parse __SERVER_DATA__ JSON (richer data)
    match = re.search(
        r"window\.__SERVER_DATA__\s*=\s*({.*?});",
        fetch_result.content,
        re.DOTALL,
    )
    if match:
        try:
            data = json.loads(match.group(1))
            events = (
                data.get("search_data", {})
                .get("events", {})
                .get("results", [])
            )
            for event in events:
                items.append(_eventbrite_event_to_candidate(event, fetch_result))
        except (json.JSONDecodeError, KeyError) as exc:
            logger.warning("Failed to parse __SERVER_DATA__: %s", exc)

    # Fallback: parse JSON-LD if __SERVER_DATA__ failed
    if not items:
        soup = BeautifulSoup(fetch_result.content, "lxml")
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                ld_data = json.loads(script.string)
                if isinstance(ld_data, dict) and "itemListElement" in ld_data:
                    for entry in ld_data["itemListElement"]:
                        event = entry.get("item", {})
                        items.append(
                            _eventbrite_jsonld_to_candidate(event, fetch_result)
                        )
            except (json.JSONDecodeError, KeyError):
                continue

    logger.info("Extracted %d items from Eventbrite", len(items))
    return items


def _eventbrite_event_to_candidate(
    event: dict, fetch_result: FetchResult
) -> CandidateItem:
    """Convert an Eventbrite __SERVER_DATA__ event to a CandidateItem."""
    venue = event.get("primary_venue", {})
    address = venue.get("address", {})

    # Build location text from address
    addr_parts = [
        address.get("address_1", ""),
        address.get("city", ""),
        address.get("region", ""),
        address.get("postal_code", ""),
    ]
    location_text = ", ".join(p for p in addr_parts if p)

    # Build date text
    date_parts = []
    if event.get("start_date"):
        start = event["start_date"]
        if event.get("start_time"):
            start += f" {event['start_time']}"
        date_parts.append(start)
    if event.get("end_date") and event["end_date"] != event.get("start_date"):
        end = event["end_date"]
        if event.get("end_time"):
            end += f" {event['end_time']}"
        date_parts.append(end)
    raw_date = " → ".join(date_parts) if date_parts else ""

    # Get image
    image_url = ""
    img = event.get("image", {})
    if img:
        sizes = img.get("image_sizes", {})
        image_url = sizes.get("large", sizes.get("medium", img.get("url", "")))

    # Classify type from tags
    item_type = "event"
    tags_text = " ".join(t.get("display_name", "") for t in event.get("tags", []))
    full_text = f"{event.get('name', '')} {event.get('summary', '')} {tags_text}"
    item_type = _classify_type(full_text)

    return CandidateItem(
        title=event.get("name", ""),
        description=event.get("summary", ""),
        item_type=item_type,
        business_name=venue.get("name", ""),
        venue_name=venue.get("name", ""),
        raw_location=location_text,
        raw_date=raw_date,
        raw_price="",
        source_url=event.get("url", fetch_result.url),
        source_name=fetch_result.source.name,
        image_url=image_url,
        raw_extracted={
            "eventbrite_id": event.get("id", ""),
            "tags": [t.get("display_name", "") for t in event.get("tags", [])],
            "timezone": event.get("timezone", ""),
            "is_online": event.get("is_online_event", False),
            "tickets_url": event.get("tickets_url", ""),
            "address": address,
        },
    )


def _eventbrite_jsonld_to_candidate(
    event: dict, fetch_result: FetchResult
) -> CandidateItem:
    """Convert an Eventbrite JSON-LD event to a CandidateItem."""
    location = event.get("location", {})
    address = location.get("address", {})

    addr_parts = [
        address.get("streetAddress", ""),
        address.get("addressLocality", ""),
        address.get("addressRegion", ""),
        address.get("postalCode", ""),
    ]
    location_text = ", ".join(p for p in addr_parts if p)

    raw_date = event.get("startDate", "")
    if event.get("endDate") and event["endDate"] != event.get("startDate"):
        raw_date += f" → {event['endDate']}"

    return CandidateItem(
        title=event.get("name", ""),
        description=event.get("description", ""),
        item_type="event",
        business_name=location.get("name", ""),
        venue_name=location.get("name", ""),
        raw_location=location_text,
        raw_date=raw_date,
        raw_price="",
        source_url=event.get("url", fetch_result.url),
        source_name=fetch_result.source.name,
        image_url=event.get("image", ""),
        raw_extracted={"jsonld": event},
    )


# --- Source routing ---

SOURCE_EXTRACTORS: dict[str, callable] = {
    "Eventbrite San Pedro F&B": extract_items_eventbrite,
}

# Sources with no known event structure — skip generic extraction
# (these are restaurant homepages with no event listings)
SKIP_GENERIC: set[str] = {
    "Grupo Pangea",
    "Pangea Restaurante",
    "Colmillo",
    "Sonora Grill Promociones",
    "Arboleda San Pedro",
    "Maverick",
}


def extract_items(fetch_result: FetchResult) -> list[CandidateItem]:
    """Main entry point: extract items from a fetch result.

    Routes to per-source extractors when available,
    falls back to the generic extractor (unless source is in SKIP_GENERIC).
    """
    extractor = SOURCE_EXTRACTORS.get(fetch_result.source.name)
    if extractor:
        return extractor(fetch_result)
    if fetch_result.source.name in SKIP_GENERIC:
        logger.info("Skipping %s (no extractor, no events)", fetch_result.source.name)
        return []
    return extract_items_generic(fetch_result)
