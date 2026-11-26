"""Frozen dashboard vocabularies. Reject or flag any value that is not an exact label."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable

import yaml

from ts_monitor.paths import default_vocabularies_path

FIELD_ENUM = {
    "status": "status",
    "service_type_ids": "service_type_ids",
    "service_type_id": "service_type_ids",
    "obligation_type": "obligation_type",
    "obligation_types": "obligation_type",
    "type": "obligation_type",
    "milestone_type": "milestone_type",
    "instrument_kind": "instrument_kind",
    "kind": "instrument_kind",
    "action": "proposal_action",
    "market_obligation_ids": "market_obligation_ids",
    "obligation_ids": "market_obligation_ids",
}

# Market-layer identifiers that are sometimes mistakenly used as regulation obligation types.
MARKET_ONLY = {"age_assurance", "risk_assessment", "transparency_reporting", "user_empowerment", "ai_transparency"}


@lru_cache(maxsize=4)
def load_vocabularies(path: str | Path | None = None) -> dict[str, list[str]]:
    location = Path(path) if path else default_vocabularies_path()
    raw = yaml.safe_load(location.read_text(encoding="utf-8"))
    out: dict[str, list[str]] = {}
    for key, value in raw.items():
        if isinstance(value, list):
            out[key] = [str(item) for item in value]
    return out


def allowed(enum_name: str, vocab: dict[str, list[str]] | None = None) -> set[str]:
    table = vocab or load_vocabularies()
    return set(table.get(enum_name, []))


def validate_value(enum_name: str, value: str, vocab: dict[str, list[str]] | None = None) -> str | None:
    """Return a flag message if the value is not in the frozen enum, else None."""
    permitted = allowed(enum_name, vocab)
    if value in permitted:
        return None
    if enum_name == "obligation_type" and value in MARKET_ONLY:
        return (
            f"obligation type {value!r} is a market-layer obligation_id, "
            "not a frozen regulation obligation type"
        )
    return f"{enum_name} value {value!r} is not in the frozen enum"


def validate_fields(fields: dict[str, Any], vocab: dict[str, list[str]] | None = None) -> list[str]:
    flags: list[str] = []
    table = vocab or load_vocabularies()
    for key, raw in fields.items():
        enum_name = FIELD_ENUM.get(key)
        if not enum_name:
            continue
        values: Iterable[str]
        if isinstance(raw, list):
            values = [str(v) for v in raw]
        elif raw is None:
            continue
        else:
            values = [str(raw)]
        for value in values:
            flag = validate_value(enum_name, value, table)
            if flag:
                flags.append(flag)
        # Nested obligation or milestone objects.
    for key in ("obligations", "milestones"):
        block = fields.get(key)
        if not isinstance(block, list):
            continue
        enum_name = "obligation_type" if key == "obligations" else "milestone_type"
        for entry in block:
            if isinstance(entry, dict) and entry.get("type"):
                flag = validate_value(enum_name, str(entry["type"]), table)
                if flag:
                    flags.append(flag)
    return flags


def has_invalid_values(fields: dict[str, Any], vocab: dict[str, list[str]] | None = None) -> bool:
    return bool(validate_fields(fields, vocab))
