"""Pipeline orchestrator — runs all modules in order."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from feed_extractor.config import OUTPUT_DIR
from feed_extractor.models import CandidateItem, CanonicalItem, LocationResult, TemporalResult
from feed_extractor.modules.dedup import deduplicate
from feed_extractor.modules.extractor import extract_items
from feed_extractor.modules.fetcher import fetch_all_sources, fetch_result_to_log_dict
from feed_extractor.modules.locator import apply_source_relevance, resolve_location
from feed_extractor.modules.scorer import score_all
from feed_extractor.modules.sources import load_san_pedro_places, load_sources_from_file, sources_to_dicts
from feed_extractor.modules.temporal import resolve_temporal

logger = logging.getLogger(__name__)


def run_pipeline(*, skip_db: bool = False) -> list[CanonicalItem]:
    """Execute the full feed extraction pipeline.

    Args:
        skip_db: If True, skip all Supabase operations (useful for testing).

    Returns:
        List of scored canonical items.
    """
    # --- Module 1: Load sources ---
    logger.info("=== Module 1: Loading sources ===")
    sources = load_sources_from_file()
    places_data = load_san_pedro_places()
    logger.info("Loaded %d sources", len(sources))

    if not skip_db:
        from feed_extractor.db import upsert_sources
        upsert_sources(sources_to_dicts(sources))

    # --- Module 2: Fetch ---
    logger.info("=== Module 2: Fetching sources ===")
    fetch_results = fetch_all_sources(sources)

    if not skip_db:
        from feed_extractor.db import get_active_sources, insert_fetch_log
        db_sources = get_active_sources()
        url_to_id = {s["base_url"]: s["id"] for s in db_sources}
        for result in fetch_results:
            source_id = url_to_id.get(result.url)
            insert_fetch_log(fetch_result_to_log_dict(result, source_id))

    successful = [r for r in fetch_results if r.ok]
    logger.info("Fetched %d/%d sources successfully", len(successful), len(fetch_results))

    # --- Module 3: Extract ---
    logger.info("=== Module 3: Extracting items ===")
    all_candidates: list[CandidateItem] = []
    for result in successful:
        items = extract_items(result)
        all_candidates.extend(items)
    logger.info("Extracted %d total candidate items", len(all_candidates))

    if not all_candidates:
        logger.warning("No items extracted. Pipeline complete.")
        return []

    # --- Module 4: San Pedro resolver ---
    logger.info("=== Module 4: Resolving locations ===")
    resolved: list[tuple[CandidateItem, LocationResult, TemporalResult]] = []
    dropped = 0

    for item in all_candidates:
        loc = resolve_location(item, places_data)

        # Apply source-level relevance boost
        source = next(
            (s for s in sources if s.name == item.source_name), None
        )
        if source:
            loc = apply_source_relevance(loc, source.relevance_type)

        if not loc.is_san_pedro:
            dropped += 1
            continue

        # --- Module 5: Time validity ---
        temp = resolve_temporal(item)

        # Drop expired items
        if temp.status == "expired":
            dropped += 1
            continue

        resolved.append((item, loc, temp))

    logger.info(
        "Location + time filter: %d kept, %d dropped",
        len(resolved),
        dropped,
    )

    if not resolved:
        logger.warning("No items passed filters. Pipeline complete.")
        return []

    # --- Module 6: Deduplication ---
    logger.info("=== Module 6: Deduplicating ===")
    canonical = deduplicate(resolved)

    # --- Module 7: Scoring ---
    logger.info("=== Module 7: Scoring ===")
    scored = score_all(canonical)

    # --- Module 8: Output ---
    logger.info("=== Module 8: Output ===")

    if not skip_db:
        from feed_extractor.db import upsert_items
        upsert_items([_item_to_dict(item) for item in scored])
        logger.info("Upserted %d items to Supabase", len(scored))

    _write_output_files(scored)

    logger.info("=== Pipeline complete: %d items ===", len(scored))
    return scored


def _item_to_dict(item: CanonicalItem) -> dict:
    """Convert a CanonicalItem to a dict for Supabase upsert."""
    d = asdict(item)
    # Remove None values to let DB defaults work
    return {k: v for k, v in d.items() if v is not None}


def _write_output_files(items: list[CanonicalItem]) -> None:
    """Write JSON and Markdown output files."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # JSON
    json_path = OUTPUT_DIR / f"feed_{today}.json"
    data = [asdict(item) for item in items]
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)
    logger.info("Wrote %s", json_path)

    # Markdown
    md_path = OUTPUT_DIR / f"feed_{today}.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# Feed San Pedro — {today}\n\n")
        f.write(f"Total items: {len(items)}\n\n---\n\n")

        for i, item in enumerate(items, 1):
            f.write(f"## {i}. {item.title}\n\n")
            f.write(f"- **Type:** {item.item_type}\n")
            f.write(f"- **Business:** {item.business_name}\n")
            if item.venue_name and item.venue_name != item.business_name:
                f.write(f"- **Venue:** {item.venue_name}\n")
            if item.matched_place:
                f.write(f"- **Place:** {item.matched_place}\n")
            if item.address_text:
                f.write(f"- **Address:** {item.address_text}\n")
            if item.start_datetime:
                f.write(f"- **Date:** {item.start_datetime}")
                if item.end_datetime:
                    f.write(f" → {item.end_datetime}")
                f.write("\n")
            if item.valid_until:
                f.write(f"- **Valid until:** {item.valid_until}\n")
            if item.price_text:
                f.write(f"- **Price/Discount:** {item.price_text}\n")
            f.write(f"- **Status:** {item.status}\n")
            f.write(f"- **Score:** {item.quality_score:.3f}\n")
            f.write(f"- **Confidence:** {item.location_confidence:.2f}\n")
            if item.summary:
                f.write(f"\n{item.summary}\n")
            for url in item.source_urls:
                f.write(f"\n- Source: {url}\n")
            f.write(f"\n---\n\n")

    logger.info("Wrote %s", md_path)
