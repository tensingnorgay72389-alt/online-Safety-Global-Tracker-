from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from ts_monitor.official_inventory import load_official_inventory, row_on_weekly_poll, sources_for_poll
from ts_monitor.sources import load_catalog

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
        "pollable": 971,
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
    weekly = sources_for_poll(inventory)
    weekly_urls = {source.url for source in weekly}
    assert len(weekly) == 364
    assert len({source.id for source in weekly}) == 364
    assert all(source.auto_apply_eligible is False for source in weekly)
    assert dsit["url"] not in weekly_urls
    blocked = [row for row in inventory.rows if row["verification_status"] == "unverified-blocked"]
    assert len(blocked) == 70
    assert any(row["http_status"] == "403" for row in blocked)
    weekly_blocked = [row for row in blocked if row_on_weekly_poll(row)]
    assert weekly_blocked
    assert all(row["url"] in weekly_urls for row in weekly_blocked)
    assert len(load_catalog().sources) == 54
