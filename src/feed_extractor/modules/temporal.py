"""Module 5: Time validity resolver — parse dates and classify freshness."""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone

from dateutil import parser as dateutil_parser

from feed_extractor.models import CandidateItem, TemporalResult

logger = logging.getLogger(__name__)

# Spanish month names → month numbers
SPANISH_MONTHS = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4,
    "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
    "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
}


def _parse_spanish_date(text: str, default_year: int | None = None) -> datetime | None:
    """Try to parse a Spanish date string like '15 de marzo de 2026'."""
    if default_year is None:
        default_year = datetime.now(timezone.utc).year

    # "15 de marzo de 2026" or "15 de marzo"
    m = re.search(
        r"(\d{1,2})\s+de\s+(\w+)(?:\s+de\s+(\d{4}))?", text, re.IGNORECASE
    )
    if m:
        day = int(m.group(1))
        month_name = m.group(2).lower()
        year = int(m.group(3)) if m.group(3) else default_year
        month = SPANISH_MONTHS.get(month_name)
        if month:
            try:
                return datetime(year, month, day, tzinfo=timezone.utc)
            except ValueError:
                pass

    # Try standard dateutil parsing as fallback
    try:
        return dateutil_parser.parse(text, fuzzy=True).replace(tzinfo=timezone.utc)
    except (ValueError, OverflowError):
        return None


def _parse_date_range(text: str) -> tuple[datetime | None, datetime | None]:
    """Try to parse a date range like 'del 15 al 30 de marzo'."""
    m = re.search(
        r"del?\s+(\d{1,2})\s+al\s+(\d{1,2})\s+de\s+(\w+)(?:\s+de\s+(\d{4}))?",
        text,
        re.IGNORECASE,
    )
    if m:
        day_start = int(m.group(1))
        day_end = int(m.group(2))
        month_name = m.group(3).lower()
        year = int(m.group(4)) if m.group(4) else datetime.now(timezone.utc).year
        month = SPANISH_MONTHS.get(month_name)
        if month:
            try:
                start = datetime(year, month, day_start, tzinfo=timezone.utc)
                end = datetime(year, month, day_end, tzinfo=timezone.utc)
                return start, end
            except ValueError:
                pass
    return None, None


def _parse_valid_until(text: str) -> datetime | None:
    """Parse 'hasta' / 'vigente hasta' patterns."""
    m = re.search(
        r"(?:hasta|vigente\s+hasta)\s+(?:el\s+)?(.+?)(?:[.;,]|$)",
        text,
        re.IGNORECASE,
    )
    if m:
        return _parse_spanish_date(m.group(1).strip())
    return None


def resolve_temporal(item: CandidateItem) -> TemporalResult:
    """Parse dates from a candidate item and classify its time status."""
    now = datetime.now(timezone.utc)
    result = TemporalResult()

    # Combine all date-bearing text
    date_text = f"{item.raw_date} {item.description}"

    # Try date range first
    start, end = _parse_date_range(date_text)
    if start:
        result.start_datetime = start
    if end:
        result.end_datetime = end

    # Try valid_until
    valid_until = _parse_valid_until(date_text)
    if valid_until:
        result.valid_until = valid_until

    # If no range found, try single date
    if not result.start_datetime and item.raw_date:
        parsed = _parse_spanish_date(item.raw_date)
        if parsed:
            result.start_datetime = parsed

    # Classify status
    result.status = _classify_status(result, now)

    logger.debug(
        "Temporal: '%s' → %s (start=%s, end=%s, until=%s)",
        item.title[:40],
        result.status,
        result.start_datetime,
        result.end_datetime,
        result.valid_until,
    )

    return result


def _classify_status(result: TemporalResult, now: datetime) -> str:
    """Classify an item as upcoming, active, expired, or unknown."""
    end = result.end_datetime or result.valid_until

    if end and end < now:
        return "expired"

    if result.start_datetime:
        if result.start_datetime > now:
            return "upcoming"
        if end and end >= now:
            return "active"
        # Start is in the past but no end date — assume still active if recent
        days_ago = (now - result.start_datetime).days
        if days_ago <= 30:
            return "active"
        return "expired"

    if result.valid_until and result.valid_until >= now:
        return "active"

    return "unknown"
