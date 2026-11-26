"""Timestamps in Asia/Hong_Kong and UTC."""

from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

HONG_KONG = ZoneInfo("Asia/Hong_Kong")
UTC = timezone.utc


def parse_datetime(value: str | datetime | None) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=HONG_KONG)
        return value
    text = value.strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=HONG_KONG)
    return parsed


def to_hong_kong(value: datetime) -> datetime:
    if value.tzinfo is None:
        value = value.replace(tzinfo=HONG_KONG)
    return value.astimezone(HONG_KONG)


def to_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        value = value.replace(tzinfo=HONG_KONG)
    return value.astimezone(UTC)


def iso(value: datetime) -> str:
    return value.isoformat()


def pair_from(value: str | datetime | None, fallback: datetime | None = None) -> tuple[str, str]:
    """Return (Hong Kong ISO 8601, UTC ISO 8601)."""
    parsed = parse_datetime(value) or fallback or datetime.now(tz=HONG_KONG)
    hk = to_hong_kong(parsed)
    utc = to_utc(parsed)
    return iso(hk), iso(utc)


def now_pair() -> tuple[str, str]:
    return pair_from(datetime.now(tz=UTC))
