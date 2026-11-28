"""Load the expanded official-source inventory for the weekly official poll.

``ts-monitor intake`` fetches the approved weekly markets from this file.
``ts-monitor run`` fetches it only when a run passes
``--include-official-inventory``, and then only those same markets. Rows stay
in the inventory when an official URL returns 403, times out or is otherwise
blocked, and when the market is outside the weekly set. Those rows are not
treated as dead and they are not deleted. Weekly poll rows are official
addresses only. They are not auto-apply eligible and this module does not
write the register or change a market score.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ts_monitor.paths import default_official_inventory_path
from ts_monitor.sources import Source
from ts_monitor.weekly_markets import WEEKLY_OFFICIAL_MARKET_IDS

_METHODS = {
    "rss": "rss",
    "json-api": "official_page",
    "legislation": "html_index",
    "html-list": "html_index",
}


@dataclass(frozen=True)
class OfficialInventory:
    as_of: str
    rows: list[dict[str, Any]]

    def counts(self) -> dict[str, int]:
        added = [row for row in self.rows if row.get("row_origin") == "added"]
        return {
            "rows": len(self.rows),
            "original": sum(1 for row in self.rows if row.get("row_origin") == "original"),
            "added": len(added),
            "verified": sum(1 for row in added if row.get("verification_status") == "verified"),
            "unverified_blocked": sum(1 for row in added if row.get("verification_status") == "unverified-blocked"),
            "unverified": sum(1 for row in added if row.get("verification_status") == "unverified"),
            "pollable": sum(1 for row in self.rows if row_is_pollable(row)),
        }


def load_official_inventory(path: str | Path | None = None) -> OfficialInventory:
    location = Path(path) if path else default_official_inventory_path()
    raw = json.loads(location.read_text(encoding="utf-8"))
    rows = list(raw.get("sources") or [])
    return OfficialInventory(as_of=str(raw.get("as_of") or ""), rows=rows)


def row_is_pollable(row: dict[str, Any]) -> bool:
    """True when the row has an official URL and ``poll`` is not false.

    ``unverified-blocked``, ``unverified``, a blank verification status and
    HTTP 403 all stay in this set. Only a missing URL or ``poll: false`` is
    skipped. The weekly monitor then keeps the approved markets; see
    ``row_on_weekly_poll``.
    """
    if not str(row.get("url") or "").strip():
        return False
    poll = row.get("poll")
    if poll is False:
        return False
    if isinstance(poll, str) and poll.strip().upper() == "FALSE":
        return False
    return True


def row_on_weekly_poll(row: dict[str, Any]) -> bool:
    """True when the weekly official monitor should request this URL.

    A row stays in the inventory either way. A missing URL, ``poll: false``
    (the retired UK DSIT row) and any ``market_id`` outside the approved set
    are left off the weekly poll. Blocked URLs inside the approved set stay on it.
    """
    if not row_is_pollable(row):
        return False
    market_id = str(row.get("market_id") or "").strip().lower()
    return market_id in WEEKLY_OFFICIAL_MARKET_IDS


def sources_for_poll(inventory: OfficialInventory) -> list[Source]:
    """Build fetch sources for the weekly approved markets.

    Blocked URLs in those markets stay in the poll. Rows for every other
    market stay in the inventory and are not returned.

    Duplicate ``source_id`` values are kept as separate sources. The second and
    later copies gain a row suffix so the catalogue can hold both URLs.
    """
    seen: dict[str, int] = {}
    sources: list[Source] = []
    for row in inventory.rows:
        if not row_on_weekly_poll(row):
            continue
        base = str(row.get("source_id") or f"official-row-{row.get('row_number')}").strip()
        seen[base] = seen.get(base, 0) + 1
        source_id = base if seen[base] == 1 else f"{base}~{row.get('row_number')}"
        status = str(row.get("verification_status") or "unset")
        http_status = str(row.get("http_status") or "unset")
        sources.append(
            Source(
                id=source_id,
                name=str(row.get("source_name") or source_id),
                url=str(row["url"]).strip(),
                method=_METHODS.get(str(row.get("adapter") or ""), "html_index"),
                official=True,
                auto_apply_eligible=False,
                role="signal_source",
                jurisdiction=str(row.get("market_id") or "").strip() or None,
                notes=(
                    f"Official inventory row {row.get('row_number')}. "
                    f"verification_status={status}. http_status={http_status}. "
                    "Blocked official URLs remain pollable. "
                    "Not auto-applied and not written into the register."
                ),
            )
        )
    return sources
