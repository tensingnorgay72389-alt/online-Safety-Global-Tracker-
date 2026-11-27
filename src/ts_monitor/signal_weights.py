"""Map an actor onto the 0 to 1 Signals weight scale.

The numeric weight is what the Signals page sorts and thresholds on.
High, medium and low remain labels. These weights do not change market scores.
"""

from __future__ import annotations

WEIGHT_HIGH = 0.90
WEIGHT_MEDIUM_MECHANISM = 0.65
WEIGHT_MEDIUM_REVIEW = 0.50
WEIGHT_LOW = 0.25


def band_for_weight(weight: float | None) -> str | None:
    if weight is None:
        return None
    if weight >= WEIGHT_HIGH:
        return "high"
    if weight >= WEIGHT_MEDIUM_REVIEW:
        return "medium"
    return "low"


def actor_weight(
    actor_class: str | None,
    specific_risk_or_mechanism: bool,
    *,
    speaking_as_department: bool = False,
) -> float | None:
    """Return 0.90, 0.65, 0.50 or 0.25. Unknown actors stay unset."""
    kind = (actor_class or "").strip().lower()
    if not kind:
        return None
    if "ngo" in kind or "civil society" in kind:
        return WEIGHT_LOW
    medium = WEIGHT_MEDIUM_MECHANISM if specific_risk_or_mechanism else WEIGHT_MEDIUM_REVIEW
    if any(token in kind for token in ("senate president", "committee chair", "former")):
        return medium
    deputy = any(token in kind for token in ("deputy", "minister of state", "junior minister"))
    if deputy:
        return WEIGHT_HIGH if speaking_as_department else medium
    high_markers = (
        "minister",
        "head of government",
        "president",
        "european commissioner",
        "regulator head",
        "statutory regulator",
        "law-enforcement",
    )
    if any(marker in kind for marker in high_markers):
        return WEIGHT_HIGH
    return medium
