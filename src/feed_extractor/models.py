"""Data models for the feed extraction pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Source:
    """A curated web source to scrape."""

    id: str | None = None
    name: str = ""
    base_url: str = ""
    source_type: str = ""  # website, calendar, promo_page, social
    fetch_method: str = "html"  # html, api, rss
    content_type: str = "mixed"  # events, promos, mixed
    trust_score: float = 0.5
    relevance_type: str = "exclusive_to_san_pedro"
    active: bool = True


@dataclass
class FetchResult:
    """Result of fetching a single source."""

    source: Source
    url: str = ""
    status_code: int = 0
    content: str = ""
    content_hash: str = ""
    fetched_at: str = ""
    error: str | None = None

    @property
    def ok(self) -> bool:
        return 200 <= self.status_code < 400 and self.error is None


@dataclass
class CandidateItem:
    """A raw extracted item before location/time resolution."""

    title: str = ""
    description: str = ""
    item_type: str = ""  # event, promo, discount
    business_name: str = ""
    venue_name: str = ""
    raw_location: str = ""
    raw_date: str = ""
    raw_price: str = ""
    source_url: str = ""
    source_name: str = ""
    image_url: str = ""
    raw_extracted: dict = field(default_factory=dict)


@dataclass
class LocationResult:
    """Output of the San Pedro location resolver."""

    is_san_pedro: bool = False
    location_confidence: float = 0.0
    matched_place: str = ""
    address_text: str = ""
    municipality: str = ""


@dataclass
class TemporalResult:
    """Output of the time validity resolver."""

    start_datetime: datetime | None = None
    end_datetime: datetime | None = None
    valid_until: datetime | None = None
    status: str = "unknown"  # upcoming, active, expired, unknown


@dataclass
class CanonicalItem:
    """A fully resolved, deduplicated feed item ready for storage."""

    canonical_id: str = ""
    item_type: str = ""
    title: str = ""
    summary: str = ""
    business_name: str = ""
    venue_name: str = ""
    address_text: str = ""
    municipality: str = "San Pedro Garza García"
    is_san_pedro: bool = True
    location_confidence: float = 0.0
    matched_place: str = ""
    start_datetime: str | None = None
    end_datetime: str | None = None
    valid_until: str | None = None
    price_text: str = ""
    discount_text: str = ""
    terms_text: str = ""
    image_url: str = ""
    source_urls: list[str] = field(default_factory=list)
    source_names: list[str] = field(default_factory=list)
    source_count: int = 1
    first_seen_at: str = ""
    last_seen_at: str = ""
    status: str = "unknown"
    quality_score: float = 0.0
    raw_extracted: dict = field(default_factory=dict)
