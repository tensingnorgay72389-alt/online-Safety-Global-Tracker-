"""Weekly official monitor: approved markets, Monday schedule, seven-day lookback."""

from __future__ import annotations

import json
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

from ts_monitor.cli import assemble_weekly_fetch_catalog, main
from ts_monitor.official_intake import sources_to_collect
from ts_monitor.official_inventory import load_official_inventory, row_on_weekly_poll, sources_for_poll
from ts_monitor.regulators import load_regulator_map, sources_for_weekly_run
from ts_monitor.sources import load_catalog
from ts_monitor.weekly_markets import (
    WEEKLY_LOOKBACK_DAYS,
    WEEKLY_OFFICIAL_MARKET_IDS,
    weekly_since,
)

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "monitor.yml"

APPROVED = {
    "eu",
    "gb",
    "au",
    "de",
    "us",
    "br",
    "fr",
    "sg",
    "ie",
    "mm",
    "nl",
    "mx",
    "tr",
    "id",
    "it",
    "es",
    "kr",
    "in",
    "my",
    "at",
    "vn",
    "jp",
    "ph",
    "th",
    "ca",
    "kh",
    "la",
    "bn",
    "pk",
}
ASEAN = {"bn", "kh", "id", "la", "my", "mm", "ph", "sg", "th", "vn"}
WEEKLY_URLS_BY_MARKET = {
    "at": 9,
    "au": 21,
    "bn": 4,
    "br": 18,
    "ca": 16,
    "de": 15,
    "es": 11,
    "eu": 32,
    "fr": 14,
    "gb": 24,
    "id": 9,
    "ie": 8,
    "in": 17,
    "it": 10,
    "jp": 12,
    "kh": 5,
    "kr": 11,
    "la": 3,
    "mm": 4,
    "mx": 13,
    "my": 13,
    "nl": 10,
    "ph": 19,
    "pk": 8,
    "sg": 14,
    "th": 7,
    "tr": 11,
    "us": 16,
    "vn": 10,
}


def test_approved_markets_stay_on_the_weekly_inventory_poll():
    assert WEEKLY_OFFICIAL_MARKET_IDS == APPROVED
    assert ASEAN <= WEEKLY_OFFICIAL_MARKET_IDS
    assert "gr" not in WEEKLY_OFFICIAL_MARKET_IDS
    assert "no" not in WEEKLY_OFFICIAL_MARKET_IDS
    assert "kp" not in WEEKLY_OFFICIAL_MARKET_IDS
    assert "tl" not in WEEKLY_OFFICIAL_MARKET_IDS

    inventory = load_official_inventory()
    weekly = sources_to_collect(inventory)
    assert [source.url for source in sources_for_poll(inventory)] == [row["url"] for row in weekly]
    assert Counter(row["market_id"] for row in weekly) == WEEKLY_URLS_BY_MARKET
    assert len(weekly) == 364
    assert {row["market_id"] for row in weekly} == APPROVED
    assert all(row_on_weekly_poll(row) for row in weekly)
    assert not any(row["market_id"].startswith("us-") for row in weekly)
    assert any(row["market_id"] == "us" for row in weekly)
    assert any(row["market_id"] == "kr" for row in weekly)

    gb_rows = [row for row in inventory.rows if row["market_id"] == "gb"]
    assert len(gb_rows) == 25
    assert sum(1 for row in gb_rows if row_on_weekly_poll(row)) == 24
    dsit = next(row for row in gb_rows if row["source_id"] == "gb-dsit")
    assert dsit["poll"] is False
    assert dsit["url"] not in {row["url"] for row in weekly}


def test_greece_norway_and_us_states_stay_in_the_inventory_and_off_the_weekly_poll():
    inventory = load_official_inventory()
    weekly_ids = {row["market_id"] for row in sources_to_collect(inventory)}
    for market_id in ("gr", "no", "kp", "us-ca", "us-ny", "us-dc", "cn", "hk", "tw", "mo", "ae", "ru", "nz"):
        stored = [row for row in inventory.rows if row["market_id"] == market_id]
        assert stored, market_id
        assert all(str(row.get("url") or "").strip() for row in stored)
        assert all(row.get("poll") is True for row in stored)
        assert market_id not in weekly_ids
    assert not any(row["market_id"] == "tl" for row in inventory.rows)


def test_inventory_row_counts_and_score_files_stay_unchanged():
    paths = [
        ROOT / "data" / "official_sources.json",
        ROOT / "dashboard" / "data" / "markets.json",
        ROOT / "dashboard" / "data" / "regulations.json",
        ROOT / "data" / "register_snapshot.json",
    ]
    before = {path: path.read_bytes() for path in paths}
    inventory = load_official_inventory()
    sources_to_collect(inventory)
    sources_for_poll(inventory)
    catalog = assemble_weekly_fetch_catalog(load_catalog(), load_regulator_map())
    assert len(catalog.sources) == 191
    assert {path: path.read_bytes() for path in paths} == before

    raw = json.loads(before[paths[0]])
    assert raw["counts"] == {
        "rows": 972,
        "original": 671,
        "added": 301,
        "verified": 161,
        "unverified_blocked": 70,
        "unverified": 70,
        "pollable": 971,
        "mexico": 13,
        "turkiye": 11,
    }
    assert len(raw["sources"]) == 972
    assert inventory.counts()["rows"] == 972
    assert inventory.counts()["pollable"] == 971
    assert sum(1 for row in raw["sources"] if row.get("poll") is False) == 1


def test_weekly_run_catalogue_matches_the_approved_set_and_keeps_timor_leste():
    reg_map = load_regulator_map()
    assert reg_map.counts()["bodies"] == 108
    assert reg_map.counts()["scrape_targets"] == 175
    assert reg_map.by_id("gr-parliament") is not None
    assert reg_map.by_id("cn-cac") is not None
    assert reg_map.by_id("ae-cabinet") is not None
    assert reg_map.by_id("us-ca-legislature") is not None
    assert reg_map.by_id("tl-parliament") is not None

    stored = load_catalog()
    assert len(stored.sources) == 54
    assert stored.by_id("us-ca-leginfo") is not None
    assert stored.by_id("us-congress") is not None

    assert len(sources_for_weekly_run(reg_map)) == 166
    weekly = assemble_weekly_fetch_catalog(stored, reg_map)
    official = [source for source in weekly.sources if source.official]
    assert len(weekly.sources) == 191
    assert len(official) == 173
    assert sum(1 for source in weekly.sources if not source.official) == 18
    jurisdictions = {(source.jurisdiction or "").lower() for source in official}
    assert jurisdictions <= (APPROVED | {"tl"})
    assert "tl" in jurisdictions
    assert "us" in jurisdictions
    assert "gr" not in jurisdictions
    assert "no" not in jurisdictions
    assert "cn" not in jurisdictions
    assert "ae" not in jurisdictions
    assert not any(code.startswith("us-") for code in jurisdictions)
    assert any(source.url == "https://www.parlamento.tl/" for source in official)
    assert "us-ca-leginfo" not in {source.id for source in weekly.sources}
    assert "us-congress" in {source.id for source in weekly.sources}
    assert "news-reuters" in {source.id for source in weekly.sources}
    assert "at" not in jurisdictions
    assert "pk" not in jurisdictions

    with_inventory = assemble_weekly_fetch_catalog(stored, reg_map, include_official_inventory=True)
    widened = {(source.jurisdiction or "").lower() for source in with_inventory.sources if source.official}
    assert "at" in widened and "pk" in widened
    assert "gr" not in widened and "us-ca" not in widened and "kp" not in widened


def test_schedule_is_monday_morning_hong_kong_with_a_seven_day_lookback():
    assert WEEKLY_LOOKBACK_DAYS == 7
    monday = date(2026, 11, 30)
    assert monday.weekday() == 0
    assert weekly_since(monday) == "2026-11-23"
    assert (monday - date.fromisoformat(weekly_since(monday))).days == 7
    assert weekly_since(monday) != (monday - timedelta(days=1)).isoformat()
    assert date.fromisoformat(weekly_since(monday)).weekday() == 0

    hong_kong = datetime(2026, 11, 30, 1, 0, tzinfo=timezone.utc).astimezone(ZoneInfo("Asia/Hong_Kong"))
    assert hong_kong.hour == 9 and hong_kong.minute == 0 and hong_kong.weekday() == 0

    text = WORKFLOW.read_text(encoding="utf-8")
    assert text.startswith("name: Weekly official monitor\n")
    loaded = yaml.safe_load(text)
    trigger = loaded.get(True, loaded.get("on"))
    assert trigger["schedule"][0]["cron"] == "0 1 * * 1"
    assert "workflow_dispatch" in trigger
    assert "push" in trigger and "pull_request" in trigger
    assert "1-5" not in text
    assert "yesterday" not in text

    monitor = text.split("name: Run the monitor", 1)[1].split("name: Upload monitor artefacts", 1)[0]
    assert 'SINCE="$(ts-monitor weekly-since)"' in monitor
    assert 'ts-monitor run --since "${SINCE}"' in monitor
    assert 'ts-monitor intake --since "${SINCE}"' in monitor
    assert "--include-official-inventory" not in monitor
    live, offline = monitor.split("\n          else\n", 1)
    assert "ts-monitor intake" in live
    assert "ts-monitor intake" not in offline
    assert "--offline" in offline
    assert "tests/fixtures/inbox/all_required.json" in offline


def test_weekly_since_command_uses_the_seven_day_window(capsys, monkeypatch):
    import ts_monitor.weekly_markets as weekly_markets

    fixed = datetime(2026, 11, 30, 1, 0, tzinfo=timezone.utc)

    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return fixed

    monkeypatch.setattr(weekly_markets, "datetime", Clock)
    assert main(["weekly-since"]) == 0
    assert capsys.readouterr().out.strip() == "2026-11-23"
