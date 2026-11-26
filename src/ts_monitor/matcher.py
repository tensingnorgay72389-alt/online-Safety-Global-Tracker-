"""Match inbox items against the instrument register snapshot."""

from __future__ import annotations

from ts_monitor.models import InboxItem, MatchResult, RegisterInstrument
from ts_monitor.register import Register, normalise_name

_STOP = {
    "the", "and", "of", "for", "to", "a", "an", "on", "in", "bill", "act",
    "amendment", "law", "online", "safety", "digital",
}


def _tokens(value: str) -> set[str]:
    return {tok for tok in normalise_name(value).split() if tok and tok not in _STOP and len(tok) > 2}


def score_instrument(item: InboxItem, instrument: RegisterInstrument) -> tuple[float, str]:
    text = normalise_name(item.text())
    if instrument.id.lower() in text.replace(" ", "") or instrument.id.lower() in text:
        return 1.0, f"explicit instrument id {instrument.id}"
    best = 0.0
    reason = "no alias overlap"
    for alias in instrument.aliases:
        if not alias:
            continue
        if alias in text:
            weight = 0.95 if len(alias) > 12 else 0.8
            if weight > best:
                best = weight
                reason = f"alias {alias!r}"
    # Token overlap on the official name, with a jurisdiction bonus.
    name_tokens = _tokens(instrument.name) | _tokens(instrument.official_title or "")
    item_tokens = _tokens(item.text())
    if name_tokens and item_tokens:
        overlap = len(name_tokens & item_tokens) / len(name_tokens)
        if overlap >= 0.6:
            bonus = 0.1 if instrument.jurisdiction_id and (item.jurisdiction_hint or "") == instrument.jurisdiction_id else 0.0
            score = min(0.9, 0.55 + overlap * 0.3 + bonus)
            if score > best:
                best = score
                reason = f"name token overlap {overlap:.2f}"
    # URL overlap with the instrument's official source.
    item_url = (item.official_document_url or item.url or "").lower()
    if instrument.source_url and instrument.source_url.lower().rstrip("/") in item_url.rstrip("/"):
        if 0.92 > best:
            best = 0.92
            reason = "same official source URL"
    return best, reason


def match_item(item: InboxItem, register: Register, threshold: float = 0.7) -> MatchResult:
    hinted = item.extra.get("instrument_id") if item.extra else None
    if hinted and register.get(str(hinted)):
        found = register.get(str(hinted))
        return MatchResult(instrument=found, score=1.0, reason="inbox instrument_id")
    best: RegisterInstrument | None = None
    best_score = 0.0
    best_reason = "no match"
    for instrument in register.instruments:
        score, reason = score_instrument(item, instrument)
        if score > best_score:
            best_score = score
            best = instrument
            best_reason = reason
    if best and best_score >= threshold:
        return MatchResult(instrument=best, score=best_score, reason=best_reason)
    return MatchResult(instrument=None, score=best_score, reason=best_reason)


def match_all(items: list[InboxItem], register: Register) -> list[tuple[InboxItem, MatchResult]]:
    return [(item, match_item(item, register)) for item in items]
