"""Load the operator-refreshed instrument register snapshot and build a matcher index."""

from __future__ import annotations

import json
import re
from pathlib import Path

from ts_monitor.models import Milestone, RegisterInstrument
from ts_monitor.paths import default_register_path

_NON_ALNUM = re.compile(r"[^a-z0-9]+")

KNOWN_ALIASES: dict[str, list[str]] = {
    "AU-DDOC-2026": [
        "digital duty of care",
        "ddoc",
        "online safety amendment (digital duty of care)",
        "online safety amendment digital duty of care bill 2026",
        "r7553",
        "australia's digital duty of care",
        "australias digital duty of care",
    ],
    "UK-CPA-2026": [
        "crime and policing act 2026",
        "crime and policing act",
    ],
    "UK-OSA-2023": [
        "online safety act 2023",
        "online safety act",
    ],
    "CA-C34-2026": [
        "bill c-34",
        "safe social media act",
        "c-34",
    ],
}


def normalise_name(value: str | None) -> str:
    if not value:
        return ""
    text = value.lower().replace("&", " and ")
    text = _NON_ALNUM.sub(" ", text)
    return re.sub(r"\s+", " ", text).strip()


def _aliases_for(row: dict) -> list[str]:
    aliases = [
        normalise_name(row.get("name")),
        normalise_name(row.get("official_title")),
        normalise_name(row.get("id")),
    ]
    aliases.extend(normalise_name(a) for a in KNOWN_ALIASES.get(row["id"], []))
    return [a for a in aliases if a]


class Register:
    def __init__(self, instruments: list[RegisterInstrument], meta: dict | None = None):
        self.instruments = instruments
        self.meta = meta or {}
        self.by_id = {item.id: item for item in instruments}

    def get(self, instrument_id: str | None) -> RegisterInstrument | None:
        if not instrument_id:
            return None
        return self.by_id.get(instrument_id)


def load_register(path: str | Path | None = None) -> Register:
    location = Path(path) if path else default_register_path()
    raw = json.loads(location.read_text(encoding="utf-8"))
    milestones_by_id: dict[str, list[Milestone]] = {}
    for entry in raw.get("milestones") or []:
        rid = entry.get("rid") or entry.get("regulation_id")
        if not rid:
            continue
        milestones_by_id.setdefault(rid, []).append(
            Milestone(
                regulation_id=rid,
                type=entry.get("type") or "",
                date=entry.get("date"),
                description=entry.get("desc") or entry.get("description"),
                source_url=entry.get("source") or entry.get("source_url"),
            )
        )
    instruments: list[RegisterInstrument] = []
    for row in raw.get("regulations") or []:
        instruments.append(
            RegisterInstrument(
                id=row["id"],
                name=row.get("name") or row["id"],
                official_title=row.get("official_title"),
                jurisdiction_id=row.get("jid") or row.get("jurisdiction_id") or "",
                jurisdiction_name=row.get("jname") or row.get("jurisdiction_name"),
                year=row.get("year"),
                status=row.get("status") or "",
                instrument_kind=row.get("kind") or row.get("instrument_kind"),
                service_type_ids=list(row.get("services") or row.get("service_type_ids") or []),
                source_url=row.get("source") or row.get("source_url"),
                effective_date=row.get("effective") or row.get("effective_date"),
                summary=row.get("summary"),
                milestones=milestones_by_id.get(row["id"], []),
                aliases=_aliases_for(row),
            )
        )
    meta = {k: v for k, v in raw.items() if k not in {"regulations", "milestones"}}
    return Register(instruments=instruments, meta=meta)
