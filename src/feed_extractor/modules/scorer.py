"""Module 7: Scoring — rank items by quality and relevance."""

from __future__ import annotations

import logging

from feed_extractor.models import CanonicalItem

logger = logging.getLogger(__name__)


def score_item(item: CanonicalItem) -> float:
    """Calculate a quality score from 0.0 to 1.0 for a canonical item."""
    score = 0.0

    # +0.25: confirmed San Pedro location (high confidence)
    if item.is_san_pedro and item.location_confidence >= 0.8:
        score += 0.25
    elif item.is_san_pedro and item.location_confidence >= 0.6:
        score += 0.15

    # +0.20: active or upcoming status
    if item.status in ("active", "upcoming"):
        score += 0.20
    elif item.status == "unknown":
        score += 0.05

    # +0.15: exact venue/address known
    if item.matched_place and item.address_text:
        score += 0.15
    elif item.matched_place or item.venue_name:
        score += 0.08

    # +0.15: price or discount clearly stated
    if item.price_text or item.discount_text:
        score += 0.15

    # +0.10: item completeness
    fields = [
        item.title, item.summary, item.business_name,
        item.venue_name, item.address_text, item.start_datetime,
        item.price_text, item.image_url,
    ]
    filled = sum(1 for f in fields if f)
    completeness = filled / len(fields)
    score += 0.10 * completeness

    # +0.10: source trust (approximated by source count as proxy)
    # Real trust score would come from the source registry
    if item.source_count >= 2:
        score += 0.10
    elif item.source_count == 1:
        score += 0.05

    # +0.05: multi-source confirmation
    if item.source_count >= 3:
        score += 0.05

    # Clamp to 0.0–1.0
    return min(max(round(score, 3), 0.0), 1.0)


def score_all(items: list[CanonicalItem]) -> list[CanonicalItem]:
    """Score all items and sort by quality descending."""
    for item in items:
        item.quality_score = score_item(item)

    items.sort(key=lambda x: x.quality_score, reverse=True)

    logger.info(
        "Scored %d items. Top score: %.3f, Bottom: %.3f",
        len(items),
        items[0].quality_score if items else 0,
        items[-1].quality_score if items else 0,
    )
    return items
