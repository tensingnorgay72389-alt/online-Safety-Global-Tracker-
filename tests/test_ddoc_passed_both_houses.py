from __future__ import annotations

from tests.helpers import classify_fixture, load_fixture_item
from ts_monitor.parsers import parse_official_bill_html


def test_official_passed_both_houses_is_status_change_to_passed(pre_register, catalog, fixtures_dir):
    item, match, proposal = classify_fixture("audoc_passed_both_houses.json", pre_register, catalog)

    assert match.instrument is not None
    assert match.instrument.id == "AU-DDOC-2026"
    assert match.instrument.status == "proposed"
    assert match.instrument.instrument_kind == "bill"

    assert proposal.action == "status_change"
    assert proposal.instrument_id == "AU-DDOC-2026"
    assert proposal.fields["status"] == "passed"
    assert proposal.fields["instrument_kind"] == "bill"
    assert proposal.fields.get("signed_date") is None
    assert proposal.fields.get("effective_date") is None
    assert proposal.fields.get("passed_date") == "2026-11-25"
    assert proposal.significant is True
    assert proposal.auto_apply_eligible is True
    assert proposal.rejected is False
    assert proposal.vocabulary_flags == []
    assert proposal.previous_values["status"] == "proposed"
    assert proposal.previous_values["instrument_kind"] == "bill"
    assert proposal.sources[0].kind == "official"
    assert "parlinfo.aph.gov.au" in proposal.sources[0].url
    assert "Royal Assent" in proposal.notes or "royal assent" in proposal.notes.lower()
    assert "not an Act" in proposal.notes or "not in force" in proposal.notes.lower()
    # Epistemic mark distinguishes sourced facts from category judgement.
    sourced_fields = {row["field"] for row in proposal.epistemic.sourced_facts}
    assert "status" in sourced_fields
    assert "instrument_kind" in sourced_fields
    assert any(row["field"] == "service_type_ids" for row in proposal.epistemic.category_judgement)


def test_already_recorded_passage_is_not_a_new_significant_change(current_register, catalog):
    _, _, proposal = classify_fixture("audoc_passed_both_houses.json", current_register, catalog)
    assert proposal.fields["status"] == "passed"
    assert proposal.fields["instrument_kind"] == "bill"
    assert proposal.fields.get("signed_date") is None
    assert proposal.fields.get("effective_date") is None
    assert proposal.significant is False
    assert proposal.action == "news_only"


def test_html_parser_reads_passed_both_houses_and_no_assent(fixtures_dir):
    html = (fixtures_dir / "html" / "audoc_bill_homepage.html").read_text(encoding="utf-8")
    parsed = parse_official_bill_html(html)
    assert parsed["passed_both_houses"] is True
    assert parsed["raw_status_text"] and "Passed Both Houses" in parsed["raw_status_text"]
    assert parsed["raw_assent_listed"] is False
    assert parsed["assent_date"] is None
