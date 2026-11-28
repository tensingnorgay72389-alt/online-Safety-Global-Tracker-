from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from ts_monitor.official_inventory import load_official_inventory, sources_for_poll
from ts_monitor.sources import load_catalog
from ts_monitor.weekday_scope import is_weekday_official_market

ROOT = Path(__file__).resolve().parents[1]


def _signals() -> list[dict]:
    payload = json.loads((ROOT / "dashboard" / "data" / "signals.json").read_text(encoding="utf-8"))
    return payload["signals"]


def test_ranked_signals_keep_weights_evidence_and_markets():
    signals = _signals()
    stakeholders = json.loads((ROOT / "data" / "ranked_stakeholders.json").read_text(encoding="utf-8"))["stakeholders"]
    assert len(signals) == 218
    assert [row["id"] for row in signals] == [row["id"] for row in stakeholders]
    weights = Counter(f"{row['weight']:.2f}" for row in signals)
    assert weights == {"0.90": 91, "0.65": 21, "0.50": 82, "0.25": 24}
    by_name = {row["person_name"]: row for row in signals}
    assert by_name["Claudia Sheinbaum"]["market_id"] == "mx"
    assert by_name["Claudia Sheinbaum"]["weight"] == 0.9
    assert by_name["Mario Delgado"]["market_id"] == "mx"
    assert by_name["Mario Delgado"]["specific_risk_or_mechanism"] is True
    assert by_name["Recep Tayyip Erdogan"]["market_id"] == "tr"
    assert by_name["Raúl Torrez"]["market_id"] == "us-nm"
    assert by_name["Raúl Torrez"]["weight"] == 0.5
    assert "Keir Starmer" in by_name and "Andy Burnham" in by_name
    for row in signals:
        assert row["evidence_extract"].strip()
        assert row["source_file"].strip()
        assert row["report_date"].strip()
        assert "tencent_flag" not in row
        blob = json.dumps(row).lower()
        assert "goran" not in blob
        assert "tencent" not in blob


def test_official_inventory_preserves_rows_and_blocked_urls():
    inventory = load_official_inventory()
    counts = inventory.counts()
    assert counts == {
        "rows": 972,
        "original": 671,
        "added": 301,
        "verified": 161,
        "unverified_blocked": 70,
        "unverified": 70,
        "pollable": 364,
    }
    mx = [row for row in inventory.rows if row["market_id"] == "mx"]
    tr = [row for row in inventory.rows if row["market_id"] == "tr"]
    assert len(mx) == 13
    assert len(tr) == 11
    dsit = next(row for row in inventory.rows if row["source_id"] == "gb-dsit")
    assert dsit["status"] == "retired"
    assert dsit["verification_status"] == "stale-or-conflicting"
    assert dsit["poll"] is False
    assert "goran" not in dsit["verification_note"].lower()
    pollable = sources_for_poll(inventory)
    poll_urls = {source.url for source in pollable}
    assert len(pollable) == 364
    assert len({source.id for source in pollable}) == 364
    assert all(source.auto_apply_eligible is False for source in pollable)
    assert dsit["url"] not in poll_urls
    blocked = [row for row in inventory.rows if row["verification_status"] == "unverified-blocked"]
    assert blocked
    approved_blocked = [row for row in blocked if is_weekday_official_market(row["market_id"])]
    other_blocked = [row for row in blocked if not is_weekday_official_market(row["market_id"])]
    assert approved_blocked
    assert other_blocked
    assert all(row["url"] in poll_urls for row in approved_blocked)
    assert all(row["url"] not in poll_urls for row in other_blocked)
    assert any(row["http_status"] == "403" for row in blocked)
    assert len(load_catalog().sources) == 54
