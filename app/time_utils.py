"""UTC-only datetime helpers for storage, API, and parsing."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Any, Optional

from pydantic import BeforeValidator, PlainSerializer

UTC = timezone.utc


def utc_now() -> datetime:
    return datetime.now(UTC)


def ensure_utc(dt: datetime | None) -> datetime | None:
    """Normalize naive or aware datetimes to timezone-aware UTC."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def parse_datetime(value: Any) -> datetime | None:
    """Parse GPMS/CSV/API values into UTC-aware datetimes."""
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return ensure_utc(value)

    text = str(value).strip()
    if not text:
        return None

    iso = text
    if iso.endswith("Z"):
        iso = iso[:-1] + "+00:00"
    try:
        return ensure_utc(datetime.fromisoformat(iso))
    except ValueError:
        pass

    for fmt in (
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d %H:%M:%S",
        "%m/%d/%Y %H:%M:%S",
    ):
        try:
            return ensure_utc(datetime.strptime(text, fmt))
        except ValueError:
            continue
    return None


def format_utc_iso(dt: datetime | None) -> str | None:
    """Serialize for JSON/API as ISO-8601 with Z suffix."""
    if dt is None:
        return None
    u = ensure_utc(dt)
    assert u is not None
    text = u.strftime("%Y-%m-%dT%H:%M:%S")
    if u.microsecond:
        frac = f"{u.microsecond:06d}".rstrip("0")
        if frac:
            text += f".{frac}"
    return f"{text}Z"


def _coerce_utc_optional(value: Any) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return ensure_utc(value)
    parsed = parse_datetime(value)
    if parsed is None and value not in (None, ""):
        raise ValueError(f"Unrecognized datetime: {value!r}")
    return parsed


UtcDatetime = Annotated[
    datetime,
    BeforeValidator(_coerce_utc_optional),
    PlainSerializer(format_utc_iso, return_type=str, when_used="json"),
]

OptionalUtcDatetime = Annotated[
    Optional[datetime],
    BeforeValidator(_coerce_utc_optional),
    PlainSerializer(format_utc_iso, return_type=Optional[str], when_used="json"),
]
