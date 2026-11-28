"""Approved markets for the weekly official monitor.

``ts-monitor intake`` and the live ``ts-monitor run`` fetch official sources
only for this set. Inventory rows, regulator-map bodies and catalogue entries
outside the set stay on file. This module does not delete rows, invent URLs,
or write market scores, regulations or legislation records.

Timor-Leste is not an inventory market and is not a scored country. The
regulator map already contains its parliament page, so the weekly run keeps
that existing legislative source.

GNews queries are global keyword searches. They are not filtered here.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from ts_monitor.sources import Source, SourceCatalog

# Inclusive start date is this many UTC calendar days before the run date.
# A Monday 01:00 UTC run therefore starts on the previous Monday.
WEEKLY_LOOKBACK_DAYS = 7

# official-inventory market_id values, lowercase.
# United States means federal ``us`` rows only. ``us-*`` state and District of
# Columbia ids are outside this set. Korea means South Korea (``kr``).
# Austria and Pakistan are in this set. The regulator map and sources.yaml have
# no official URLs for them, and none are added here.
WEEKLY_OFFICIAL_MARKET_IDS = frozenset(
    {
        "eu",
        "gb",
        "au",
        "de",
        "us",
        "br",
        "fr",
        "sg",
        "ie",
        "mm",
        "nl",
        "mx",
        "tr",
        "id",
        "it",
        "es",
        "kr",
        "in",
        "my",
        "at",
        "vn",
        "jp",
        "ph",
        "th",
        "ca",
        "kh",
        "la",
        "bn",
        "pk",
    }
)

# Existing regulator-map jurisdiction kept on the weekly run. Not an inventory id.
WEEKLY_REGULATOR_EXTRA_JURISDICTIONS = frozenset({"tl"})


def jurisdiction_on_weekly_official_run(jurisdiction: str | None) -> bool:
    """True when an official catalogue jurisdiction is on the weekly run."""
    if jurisdiction is None:
        return False
    token = str(jurisdiction).strip().lower()
    if not token or token in {"null", "none"}:
        return False
    return token in WEEKLY_OFFICIAL_MARKET_IDS or token in WEEKLY_REGULATOR_EXTRA_JURISDICTIONS


def catalog_for_weekly_official_run(catalog: SourceCatalog) -> SourceCatalog:
    """Drop official sources whose jurisdiction is outside the weekly set.

    News and other non-official discovery sources stay. The returned catalogue
    is a new object; the caller's list is left as loaded from ``sources.yaml``.
    """
    kept: list[Source] = []
    for source in catalog.sources:
        if source.official and not jurisdiction_on_weekly_official_run(source.jurisdiction):
            continue
        kept.append(source)
    return SourceCatalog(sources=kept, fetch=catalog.fetch)


def weekly_since(today: date | None = None) -> str:
    """Inclusive ``YYYY-MM-DD`` start for a weekly official run.

    Uses the UTC calendar date. Seven days before a Monday run is the previous
    Monday, so items published after the previous 01:00 UTC run are still inside
    the window.
    """
    current = today or datetime.now(timezone.utc).date()
    return (current - timedelta(days=WEEKLY_LOOKBACK_DAYS)).isoformat()
