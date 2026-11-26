from __future__ import annotations

from tests.helpers import classify_fixture


def test_becomes_law_media_release_is_not_assent(pre_register, catalog):
    _, match, proposal = classify_fixture("audoc_becomes_law_media_release.json", pre_register, catalog)

    assert match.instrument is not None
    assert match.instrument.id == "AU-DDOC-2026"
    assert proposal.action == "news_only"
    assert proposal.significant is False
    assert proposal.auto_apply_eligible is False
    # Must not set instrument_kind to enacted or mark the instrument as in force.
    kind = (proposal.fields or {}).get("instrument_kind")
    status = (proposal.fields or {}).get("status")
    assert kind not in {"enacted", "in force"}
    if kind is not None:
        assert kind == "bill"
    assert status not in {"effective", "enforced", "implementation_period"}
    assert proposal.fields.get("signed_date") in (None, "")
    assert proposal.fields.get("effective_date") in (None, "")
    assert "becomes law" in proposal.notes.lower() or "royal assent" in proposal.notes.lower()


def test_becomes_law_does_not_upgrade_a_passed_bill(current_register, catalog):
    _, _, proposal = classify_fixture("audoc_becomes_law_media_release.json", current_register, catalog)
    assert proposal.action == "news_only"
    assert proposal.significant is False
    assert proposal.auto_apply_eligible is False
    assert (proposal.fields or {}).get("instrument_kind") in {None, "bill"}
    assert (proposal.fields or {}).get("status") not in {"effective", "enforced", "implementation_period"}
