"""Approved markets for the weekday official scan.

``ts-monitor intake`` and ``ts-monitor run`` both use this set. Inventory rows
for every other market stay in ``data/official_sources.json``. The run
catalogue in ``config/sources.yaml`` and ``config/regulators.yaml`` keeps those
sourced URLs as well. Weekday fetching skips official URLs outside the set.

Timor-Leste is not an inventory market. The existing legislative source on the
regulator map stays on the weekday run. No inventory URL is added for it.

GNews queries are global keyword searches. This module does not change them.
"""

from __future__ import annotations

from ts_monitor.regulators import merge_source_catalog
from ts_monitor.sources import Source, SourceCatalog

# Exact official-inventory market_id values. ``us`` is federal only.
# ``us-ca`` and the other state rows are a different id and stay out.
WEEKDAY_OFFICIAL_MARKET_IDS = frozenset(
    {
        "at",
        "au",
        "bn",
        "br",
        "ca",
        "de",
        "es",
        "eu",
        "fr",
        "gb",
        "id",
        "ie",
        "in",
        "it",
        "jp",
        "kh",
        "kr",
        "la",
        "mm",
        "mx",
        "my",
        "nl",
        "ph",
        "pk",
        "sg",
        "th",
        "tr",
        "us",
        "vn",
    }
)

# ASEAN member markets. All ten are inside the weekday set.
ASEAN_MARKET_IDS = frozenset({"bn", "kh", "id", "la", "my", "mm", "ph", "sg", "th", "vn"})

# Kept on the weekday run because the regulator map already has this legislative source.
TIMOR_LESTE_JURISDICTION = "tl"
TIMOR_LESTE_RUN_ROLE = "legislative_record"


def jurisdiction_code(value: str | None) -> str:
    return str(value or "").strip().lower()


def is_weekday_official_market(market_id: str | None) -> bool:
    """True for an approved inventory market_id. Matching is exact."""
    return jurisdiction_code(market_id) in WEEKDAY_OFFICIAL_MARKET_IDS


def include_in_weekday_run(source: Source) -> bool:
    """Whether a weekday ``ts-monitor run`` should request this catalogue source.

    News and other non-official discovery sources stay. Official sources stay
    for the approved markets. The existing Timor-Leste legislative record stays.
    """
    if not source.official:
        return True
    code = jurisdiction_code(source.jurisdiction)
    if code in WEEKDAY_OFFICIAL_MARKET_IDS:
        return True
    if code == TIMOR_LESTE_JURISDICTION and source.role == TIMOR_LESTE_RUN_ROLE:
        return True
    return False


def restrict_catalog_to_weekday_run(catalog: SourceCatalog) -> SourceCatalog:
    return SourceCatalog(
        sources=[source for source in catalog.sources if include_in_weekday_run(source)],
        fetch=catalog.fetch,
    )


def weekday_fetch_catalog(catalog: SourceCatalog, extras: list[Source]) -> SourceCatalog:
    """Merge regulator or inventory extras, then apply the weekday official gate.

    Restriction happens after the merge so an out-of-set target cannot re-enter
    through the regulator map.
    """
    return restrict_catalog_to_weekday_run(merge_source_catalog(catalog, extras))
