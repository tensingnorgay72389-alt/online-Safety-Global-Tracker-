from __future__ import annotations

import json
from pathlib import Path

from ts_monitor.cli import main
from ts_monitor.parsers import load_items_file

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"
PRE_REGISTER = FIXTURES / "register_pre_ddoc_passage.json"
ALL_REQUIRED = FIXTURES / "inbox" / "all_required.json"


def test_run_against_required_fixtures(tmp_path: Path):
    out = tmp_path / "out"
    code = main(
        [
            "run",
            "--since",
            "2026-11-24",
            "--file",
            str(ALL_REQUIRED),
            "--register",
            str(PRE_REGISTER),
            "--out",
            str(out),
            "--offline",
        ]
    )
    assert code == 0
    inbox = json.loads((out / "inbox" / "items.json").read_text(encoding="utf-8"))
    proposals = json.loads((out / "proposals" / "proposals.json").read_text(encoding="utf-8"))
    significant = json.loads((out / "significant" / "proposals.json").read_text(encoding="utf-8"))
    assert len(inbox) == 7
    assert len(proposals) == 7

    by_inbox = {row["inbox_item_id"]: row for row in proposals}

    ddoc = by_inbox["fixture-audoc-passed-both-houses-2026-11-25"]
    assert ddoc["action"] == "status_change"
    assert ddoc["fields"]["status"] == "passed"
    assert ddoc["fields"]["instrument_kind"] == "bill"
    assert ddoc["fields"]["signed_date"] is None
    assert ddoc["fields"]["effective_date"] is None
    assert ddoc["significant"] is True
    assert ddoc["auto_apply_eligible"] is True

    media = by_inbox["fixture-audoc-becomes-law-media-2026-11-25"]
    assert media["action"] == "news_only"
    assert media["significant"] is False
    assert media["fields"].get("instrument_kind") in {None, "bill"}
    assert media["fields"].get("status") not in {"effective", "enforced", "implementation_period"}

    ofcom = by_inbox["fixture-ofcom-ii-consultation-2026-11-25"]
    assert ofcom["action"] == "new_instrument"
    assert ofcom["fields"]["instrument_kind"] == "consultation"
    assert ofcom["significant"] is True

    gosrn = by_inbox["fixture-gosrn-joint-statement-2026-11-25"]
    assert gosrn["action"] == "news_only"
    assert gosrn["significant"] is False

    senators = by_inbox["fixture-us-senators-ai-safeguards-2026-11-25"]
    assert senators["action"] == "news_only"
    assert senators["significant"] is False

    brand = by_inbox["fixture-tencent-mentions-alibaba-agents-2026-10-13"]
    assert brand["action"] == "news_only"
    assert brand["significant"] is False
    assert brand["auto_apply_eligible"] is False

    vocab = by_inbox["fixture-invalid-vocabulary-labels"]
    assert vocab["rejected"] is True
    assert vocab["significant"] is False
    assert vocab["vocabulary_flags"]

    significant_ids = {row["inbox_item_id"] for row in significant}
    assert "fixture-audoc-passed-both-houses-2026-11-25" in significant_ids
    assert "fixture-ofcom-ii-consultation-2026-11-25" in significant_ids
    assert "fixture-audoc-becomes-law-media-2026-11-25" not in significant_ids
    assert "fixture-gosrn-joint-statement-2026-11-25" not in significant_ids
    assert "fixture-us-senators-ai-safeguards-2026-11-25" not in significant_ids
    assert "fixture-tencent-mentions-alibaba-agents-2026-10-13" not in significant_ids
    assert "fixture-invalid-vocabulary-labels" not in significant_ids

    # Deterministic second run.
    code2 = main(
        [
            "run",
            "--since",
            "2026-11-24",
            "--file",
            str(ALL_REQUIRED),
            "--register",
            str(PRE_REGISTER),
            "--out",
            str(out / "second"),
            "--offline",
        ]
    )
    assert code2 == 0
    again = json.loads((out / "second" / "proposals" / "proposals.json").read_text(encoding="utf-8"))
    assert proposals == again


def test_ingest_word_report_like_and_propose(tmp_path: Path):
    out = tmp_path / "out"
    report = FIXTURES / "reports" / "word_report_like.json"
    assert main(["ingest", "--file", str(report), "--out", str(out)]) == 0
    items = load_items_file(out / "inbox" / "items.json")
    assert len(items) == 1
    assert "intimate-image" in (items[0].url or "")
    assert main(["match", "--register", str(PRE_REGISTER), "--out", str(out)]) == 0
    assert (out / "inbox" / "matches.json").is_file()
    assert main(["propose", "--register", str(PRE_REGISTER), "--out", str(out)]) == 0
    proposals = json.loads((out / "proposals" / "proposals.json").read_text(encoding="utf-8"))
    assert proposals[0]["action"] == "new_instrument"
    assert proposals[0]["fields"]["instrument_kind"] == "consultation"
