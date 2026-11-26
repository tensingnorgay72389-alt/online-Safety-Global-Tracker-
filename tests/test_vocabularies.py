from __future__ import annotations

from tests.helpers import classify_fixture
from ts_monitor.vocabularies import load_vocabularies, validate_fields, validate_value


def test_frozen_enums_match_the_brief():
    vocab = load_vocabularies()
    assert vocab["status"] == [
        "proposed", "inactive", "under_review", "passed", "implementation_period",
        "effective", "enforced", "challenged", "enjoined", "repealed",
    ]
    assert "chatbot" not in vocab["service_type_ids"]
    assert "age_assurance" not in vocab["obligation_type"]
    assert "age_assurance" in vocab["market_obligation_ids"]
    assert "consultation" in vocab["instrument_kind"]
    assert "bill" in vocab["instrument_kind"]


def test_invalid_vocabulary_fixture_is_rejected(pre_register, catalog):
    _, _, proposal = classify_fixture("invalid_vocabulary.json", pre_register, catalog)
    assert proposal.rejected is True
    assert proposal.significant is False
    assert proposal.auto_apply_eligible is False
    assert proposal.vocabulary_flags
    joined = " ".join(proposal.vocabulary_flags)
    assert "becomes_law" in joined
    assert "chatbot" in joined
    assert "age_assurance" in joined
    assert "statute" in joined
    # Invalid values must not be written into apply-able fields.
    assert proposal.fields.get("status") != "becomes_law"
    assert "chatbot" not in (proposal.fields.get("service_type_ids") or [])


def test_validate_value_flags_unknown_status():
    assert validate_value("status", "passed") is None
    assert validate_value("status", "enacted") is not None
    flags = validate_fields({"obligation_types": ["age_assurance"]})
    assert flags and "market-layer" in flags[0]
