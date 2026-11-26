from __future__ import annotations

from tests.helpers import classify_fixture, load_fixture_item
from ts_monitor.classifiers import classify_item
from ts_monitor.matcher import match_item


def test_ofcom_consultation_is_new_instrument_not_cpa_enactment(pre_register, catalog):
    item, match, proposal = classify_fixture("ofcom_intimate_image_codes.json", pre_register, catalog)

    assert proposal.action == "new_instrument"
    assert proposal.proposed_id == "UK-OFCOM-IIA-CODES-2026"
    assert proposal.instrument_id is None
    assert proposal.fields["instrument_kind"] == "consultation"
    assert proposal.fields["status"] in {"proposed", "under_review"}
    assert proposal.fields.get("signed_date") is None
    assert proposal.fields.get("effective_date") is None
    assert proposal.significant is True
    assert proposal.auto_apply_eligible is True
    assert "consultation" in proposal.notes.lower()
    assert "not the enactment" in proposal.notes.lower() or "not a final code" in proposal.notes.lower()
    # Must not be treated as a status change on the Crime and Policing Act.
    assert proposal.instrument_id != "UK-CPA-2026"
    assert match.instrument is None or match.instrument.id != "UK-CPA-2026" or proposal.action == "new_instrument"


def test_ofcom_consultation_without_official_page_is_not_significant(pre_register, catalog):
    item = load_fixture_item("ofcom_intimate_image_codes.json")
    item.url = "https://www.mlex.com/mlex/articles/2559751/uk-platforms-invited-to-comment-on-intimate-image-takedown-rules"
    item.official_document_url = None
    item.source_id = "news-ap"
    item.source_kind = "news"
    match = match_item(item, pre_register)
    proposal = classify_item(item, pre_register, match.instrument, catalog)
    assert proposal.action == "new_instrument"
    assert proposal.fields["instrument_kind"] == "consultation"
    assert proposal.significant is False
    assert proposal.auto_apply_eligible is False
