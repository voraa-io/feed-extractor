"""Module 1: Source registry — load and sync curated sources."""

from __future__ import annotations

import json
from pathlib import Path

from feed_extractor.config import DATA_DIR
from feed_extractor.models import Source


def load_sources_from_file(path: Path | None = None) -> list[Source]:
    """Load curated sources from the JSON file."""
    path = path or DATA_DIR / "sources.json"
    with open(path) as f:
        raw = json.load(f)
    return [Source(**entry) for entry in raw]


def sources_to_dicts(sources: list[Source]) -> list[dict]:
    """Convert Source objects to dicts suitable for Supabase upsert."""
    results = []
    for s in sources:
        d = {
            "name": s.name,
            "base_url": s.base_url,
            "source_type": s.source_type,
            "fetch_method": s.fetch_method,
            "content_type": s.content_type,
            "trust_score": s.trust_score,
            "relevance_type": s.relevance_type,
            "active": s.active,
        }
        if s.id:
            d["id"] = s.id
        results.append(d)
    return results


def load_san_pedro_places(path: Path | None = None) -> dict:
    """Load the San Pedro places lookup table."""
    path = path or DATA_DIR / "san_pedro.json"
    with open(path) as f:
        return json.load(f)
