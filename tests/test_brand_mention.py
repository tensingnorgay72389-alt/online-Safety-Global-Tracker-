from __future__ import annotations

from tests.helpers import classify_fixture


def test_brand_mention_without_instrument_is_not_auto_applied(pre_register, catalog):
    _, match, proposal = classify_fixture("brand_mention_no_instrument.json", pre_register, catalog)
    assert match.instrument is None
    assert proposal.action == "news_only"
    assert proposal.significant is False
    assert proposal.auto_apply_eligible is False
    assert "brand mention" in proposal.notes.lower() or "no regulatory instrument" in proposal.notes.lower()
