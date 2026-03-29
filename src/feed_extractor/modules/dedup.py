"""Module 6: Deduplication — cluster and merge duplicate items."""

from __future__ import annotations

import hashlib
import logging
import re
import unicodedata
from datetime import datetime, timezone

from feed_extractor.models import CandidateItem, CanonicalItem, LocationResult, TemporalResult

logger = logging.getLogger(__name__)


def _normalize_for_dedup(text: str) -> str:
    """Normalize text for comparison: lowercase, strip accents, remove punctuation."""
    text = text.lower()
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _make_canonical_id(title: str, business: str) -> str:
    """Generate a stable canonical ID from normalized title + business."""
    key = f"{_normalize_for_dedup(title)}|{_normalize_for_dedup(business)}"
    return hashlib.sha256(key.encode()).hexdigest()[:16]


def _items_match(a: CandidateItem, b: CandidateItem) -> bool:
    """Determine if two candidate items are likely the same."""
    title_a = _normalize_for_dedup(a.title)
    title_b = _normalize_for_dedup(b.title)

    # Exact title match
    if title_a == title_b:
        return True

    # Title similarity: one contains the other
    if len(title_a) > 10 and len(title_b) > 10:
        if title_a in title_b or title_b in title_a:
            return True

    # Same business + very similar titles
    if a.business_name and a.business_name == b.business_name:
        # Check word overlap
        words_a = set(title_a.split())
        words_b = set(title_b.split())
        if words_a and words_b:
            overlap = len(words_a & words_b) / max(len(words_a), len(words_b))
            if overlap > 0.7:
                return True

    return False


def _merge_cluster(
    cluster: list[tuple[CandidateItem, LocationResult, TemporalResult]],
) -> CanonicalItem:
    """Merge a cluster of duplicate items into one canonical item."""
    # Pick the item with the longest description as the base
    cluster.sort(key=lambda x: len(x[0].description), reverse=True)
    best_item, best_loc, best_temp = cluster[0]

    # Use the location and temporal result with highest confidence
    for _, loc, _ in cluster:
        if loc.location_confidence > best_loc.location_confidence:
            best_loc = loc
    for _, _, temp in cluster:
        if temp.status != "unknown" and best_temp.status == "unknown":
            best_temp = temp

    now = datetime.now(timezone.utc).isoformat()

    return CanonicalItem(
        canonical_id=_make_canonical_id(best_item.title, best_item.business_name),
        item_type=best_item.item_type,
        title=best_item.title,
        summary=best_item.description[:300],
        business_name=best_item.business_name,
        venue_name=best_item.venue_name,
        address_text=best_loc.address_text,
        municipality=best_loc.municipality or "San Pedro Garza García",
        is_san_pedro=best_loc.is_san_pedro,
        location_confidence=best_loc.location_confidence,
        matched_place=best_loc.matched_place,
        start_datetime=best_temp.start_datetime.isoformat() if best_temp.start_datetime else None,
        end_datetime=best_temp.end_datetime.isoformat() if best_temp.end_datetime else None,
        valid_until=best_temp.valid_until.isoformat() if best_temp.valid_until else None,
        price_text=best_item.raw_price,
        discount_text=best_item.raw_price,
        image_url=best_item.image_url,
        source_urls=list({item.source_url for item, _, _ in cluster if item.source_url}),
        source_names=list({item.source_name for item, _, _ in cluster if item.source_name}),
        source_count=len(cluster),
        first_seen_at=now,
        last_seen_at=now,
        status=best_temp.status,
        raw_extracted=best_item.raw_extracted,
    )


def deduplicate(
    items_with_metadata: list[tuple[CandidateItem, LocationResult, TemporalResult]],
) -> list[CanonicalItem]:
    """Cluster candidate items and merge duplicates into canonical items."""
    if not items_with_metadata:
        return []

    # Simple greedy clustering
    clusters: list[list[tuple[CandidateItem, LocationResult, TemporalResult]]] = []
    assigned = [False] * len(items_with_metadata)

    for i, (item_a, loc_a, temp_a) in enumerate(items_with_metadata):
        if assigned[i]:
            continue
        cluster = [(item_a, loc_a, temp_a)]
        assigned[i] = True

        for j in range(i + 1, len(items_with_metadata)):
            if assigned[j]:
                continue
            item_b, loc_b, temp_b = items_with_metadata[j]
            if _items_match(item_a, item_b):
                cluster.append((item_b, loc_b, temp_b))
                assigned[j] = True

        clusters.append(cluster)

    canonical = [_merge_cluster(c) for c in clusters]
    logger.info(
        "Deduplication: %d candidates → %d clusters → %d canonical items",
        len(items_with_metadata),
        len(clusters),
        len(canonical),
    )
    return canonical
