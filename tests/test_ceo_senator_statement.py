from __future__ import annotations

from tests.helpers import classify_fixture


def test_senator_statement_with_no_bill_is_news_only(pre_register, catalog):
    _, _, proposal = classify_fixture("ceo_senator_statement.json", pre_register, catalog)
    assert proposal.action == "news_only"
    assert proposal.significant is False
    assert proposal.auto_apply_eligible is False
