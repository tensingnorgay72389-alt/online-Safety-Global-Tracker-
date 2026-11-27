"""Load the expanded official-source inventory for a later poll.

The weekday monitor does not fetch this file unless a run passes
``--include-official-inventory``. Rows stay in the inventory when an official
URL returns 403, times out or is otherwise blocked. Those rows are not treated
as dead and they are not deleted. Pollable rows are official addresses only.
They are not auto-apply eligible and this module does not write the register
or change a market score.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ts_monitor.paths import default_official_inventory_path
from ts_monitor.sources import Source

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
    """True when a later poll should request this official URL.

    ``unverified-blocked``, ``unverified``, a blank verification status and
    HTTP 403 all stay pollable. Only a missing URL or ``poll: false`` is skipped.
    """
    if not str(row.get("url") or "").strip():
        return False
    poll = row.get("poll")
    if poll is False:
        return False
    if isinstance(poll, str) and poll.strip().upper() == "FALSE":
        return False
    return True


def sources_for_poll(inventory: OfficialInventory) -> list[Source]:
    """Build fetch sources for pollable rows without dropping blocked URLs.

    Duplicate ``source_id`` values are kept as separate sources. The second and
    later copies gain a row suffix so the catalogue can hold both URLs.
    """
    seen: dict[str, int] = {}
    sources: list[Source] = []
    for row in inventory.rows:
        if not row_is_pollable(row):
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
