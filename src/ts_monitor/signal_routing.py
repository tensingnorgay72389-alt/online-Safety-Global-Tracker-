"""Route classifier output into a Signals review queue.

Confidence gates may flag items for review. They must not write regulations,
market scores or any file the heatmap and database pages display.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

CONFIDENCE_SIGNALS = 0.7
CONFIDENCE_REVIEW = 0.5
CONFIDENCE_URGENT = 0.85

PROTECTED_OUTPUT_NAMES = frozenset(
    {
        "regulations.json",
        "markets.json",
        "merged.json",
        "news_items.json",
        "jurisdictions.json",
        "service_types.json",
        "register_meta.json",
        "register_snapshot.json",
    }
)


def assert_review_output(path: Path) -> None:
    if path.name in PROTECTED_OUTPUT_NAMES:
        raise RuntimeError(
            f"Refusing to write classifier output to {path.name}. "
            "Legislation records and market scores stay unchanged until they are approved."
        )


def route_record(record: dict[str, Any]) -> dict[str, Any] | None:
    """Return a review-queue record, or None when the item is discarded.

    An unmatched high-confidence existing_regulation_development is queued
    for review. It is not discarded and it is not applied to a regulation.
    """
    action = str(record.get("action_type") or "")
    confidence = float(record.get("confidence") or 0)
    matched = bool(str(record.get("matched_regulation_id") or "").strip())
    is_signal = bool(record.get("is_signal"))
    unmatched_development = action == "existing_regulation_development" and not matched

    if action == "not_relevant" and not is_signal:
        return None
    if confidence < CONFIDENCE_REVIEW:
        return None

    urgent = confidence >= CONFIDENCE_URGENT
    if unmatched_development:
        destination = "review"
        needs_match = True
    elif confidence >= CONFIDENCE_SIGNALS:
        destination = "signals"
        needs_match = False
    else:
        destination = "review"
        needs_match = False

    queued = dict(record)
    queued.update(
        {
            "destination": destination,
            "urgent": urgent,
            "needs_match": needs_match,
            "auto_applied": False,
            "written_to_register": False,
        }
    )
    return queued


def write_review_queue(path: Path, records: list[dict[str, Any]], *, discarded: int = 0) -> dict[str, Any]:
    assert_review_output(path)
    signals = [row for row in records if row.get("destination") == "signals"]
    review = [row for row in records if row.get("destination") == "review"]
    payload = {
        "note": (
            "Review queue only. These rows are not written into regulations, "
            "market scores or the heatmap and database data."
        ),
        "signals": signals,
        "review": review,
        "urgent_count": sum(1 for row in records if row.get("urgent")),
        "discarded_count": discarded,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return payload
