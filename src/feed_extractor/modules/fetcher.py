"""Module 2: Fetcher — download raw pages from sources."""

from __future__ import annotations

import hashlib
import logging
import time
from datetime import datetime, timezone

import httpx

from feed_extractor.config import FETCH_DELAY_SECONDS, FETCH_TIMEOUT_SECONDS, USER_AGENT
from feed_extractor.models import FetchResult, Source

logger = logging.getLogger(__name__)


def _hash_content(content: str) -> str:
    return hashlib.sha256(content.encode()).hexdigest()


def fetch_source(source: Source, client: httpx.Client | None = None) -> FetchResult:
    """Fetch a single source URL and return the result."""
    own_client = client is None
    if own_client:
        client = httpx.Client(timeout=FETCH_TIMEOUT_SECONDS, follow_redirects=True)

    result = FetchResult(
        source=source,
        url=source.base_url,
        fetched_at=datetime.now(timezone.utc).isoformat(),
    )

    try:
        response = client.get(
            source.base_url,
            headers={"User-Agent": USER_AGENT},
        )
        result.status_code = response.status_code
        result.content = response.text
        result.content_hash = _hash_content(response.text)
        logger.info(
            "Fetched %s — %d (%d bytes)",
            source.name,
            response.status_code,
            len(response.text),
        )
    except httpx.HTTPError as exc:
        result.error = str(exc)
        logger.error("Failed to fetch %s: %s", source.name, exc)
    finally:
        if own_client:
            client.close()

    return result


def fetch_all_sources(sources: list[Source]) -> list[FetchResult]:
    """Fetch all sources sequentially with rate limiting."""
    results = []
    with httpx.Client(timeout=FETCH_TIMEOUT_SECONDS, follow_redirects=True) as client:
        for i, source in enumerate(sources):
            if i > 0:
                time.sleep(FETCH_DELAY_SECONDS)
            results.append(fetch_source(source, client))
    return results


def fetch_result_to_log_dict(result: FetchResult, source_id: str | None) -> dict:
    """Convert a FetchResult into a dict for the fetch_logs table."""
    return {
        "source_id": source_id,
        "url": result.url,
        "status_code": result.status_code,
        "content_hash": result.content_hash,
        "fetched_at": result.fetched_at,
    }
