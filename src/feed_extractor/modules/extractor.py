"""Module 3: Extractor — parse HTML into candidate items."""

from __future__ import annotations

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


def extract_items(fetch_result: FetchResult) -> list[CandidateItem]:
    """Main entry point: extract items from a fetch result.

    Routes to per-source extractors when available,
    falls back to the generic extractor.
    """
    # Future: add per-source extractors here
    # source_extractors = { "source_name": custom_fn }
    return extract_items_generic(fetch_result)
