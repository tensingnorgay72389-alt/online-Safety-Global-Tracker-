from __future__ import annotations

from tests.helpers import classify_fixture


def test_gosrn_joint_statement_is_news_only(pre_register, catalog):
    _, _, proposal = classify_fixture("gosrn_joint_statement.json", pre_register, catalog)
    assert proposal.action == "news_only"
    assert proposal.significant is False
    assert proposal.auto_apply_eligible is False
    assert "joint" in proposal.notes.lower() or "binding" in proposal.notes.lower()
