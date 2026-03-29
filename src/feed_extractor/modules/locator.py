"""Module 4: San Pedro resolver — determine if an item is in San Pedro."""

from __future__ import annotations

import logging
import re
import unicodedata

from feed_extractor.models import CandidateItem, LocationResult

logger = logging.getLogger(__name__)


def _normalize(text: str) -> str:
    """Lowercase, strip accents, collapse whitespace."""
    text = text.lower()
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", text).strip()


def resolve_location(item: CandidateItem, places_data: dict) -> LocationResult:
    """Determine whether a candidate item is located in San Pedro.

    Uses the places lookup table to match against known locations,
    colonias, landmarks, and municipality names.
    """
    # Build searchable text from all relevant fields
    search_fields = [
        item.title,
        item.description,
        item.raw_location,
        item.venue_name,
        item.business_name,
    ]
    raw_text = " ".join(search_fields)
    text = _normalize(raw_text)

    result = LocationResult()
    best_confidence = 0.0
    best_match = ""

    # 1. Check municipality names (highest confidence)
    for name in places_data.get("municipality_names", []):
        if _normalize(name) in text:
            best_confidence = max(best_confidence, 0.95)
            best_match = best_match or name
            result.municipality = "San Pedro Garza García"

    # 2. Check known places and their aliases
    for place in places_data.get("places", []):
        place_name = place["name"]
        names_to_check = [place_name] + place.get("aliases", [])

        for name in names_to_check:
            if len(name) < 4:
                continue
            if _normalize(name) in text:
                confidence = 0.9 if place.get("address") else 0.8
                if confidence > best_confidence:
                    best_confidence = confidence
                    best_match = place_name
                    result.address_text = place.get("address", "")
                    result.municipality = "San Pedro Garza García"

    # 3. Check colonias
    for colonia in places_data.get("colonias", []):
        if _normalize(colonia) in text:
            confidence = 0.85
            if confidence > best_confidence:
                best_confidence = confidence
                best_match = best_match or f"Colonia {colonia}"
                result.municipality = "San Pedro Garza García"

    # 4. Check landmarks (streets, avenues)
    for landmark in places_data.get("landmarks", []):
        if _normalize(landmark) in text:
            confidence = 0.7
            if confidence > best_confidence:
                best_confidence = confidence
                best_match = best_match or landmark

    # 5. Source-level relevance boost
    # If the source itself is exclusive to San Pedro, give a baseline confidence
    # even if we didn't find explicit location text
    # (This is handled by the caller based on source.relevance_type)

    result.is_san_pedro = best_confidence >= 0.6
    result.location_confidence = best_confidence
    result.matched_place = best_match

    if result.is_san_pedro:
        logger.debug(
            "SP match: '%s' → %s (%.2f)",
            item.title[:50],
            best_match,
            best_confidence,
        )
    else:
        logger.debug("No SP match: '%s'", item.title[:50])

    return result


def apply_source_relevance(
    result: LocationResult, relevance_type: str
) -> LocationResult:
    """Boost confidence for items from San Pedro-exclusive sources.

    If a source is exclusive_to_san_pedro and we didn't find explicit location
    text, give it a baseline confidence since everything on that source is local.
    """
    if relevance_type == "exclusive_to_san_pedro" and result.location_confidence < 0.6:
        result.is_san_pedro = True
        result.location_confidence = max(result.location_confidence, 0.65)
        result.matched_place = result.matched_place or "(source is SP-exclusive)"
        result.municipality = "San Pedro Garza García"
    elif relevance_type == "multi_location" and result.location_confidence < 0.5:
        # Multi-location sources need explicit evidence
        result.is_san_pedro = False

    return result
