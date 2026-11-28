"""Weekday official polling stays on the approved priority markets."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from ts_monitor.cli import main
from ts_monitor.official_intake import sources_to_collect
from ts_monitor.official_inventory import load_official_inventory, sources_for_poll
from ts_monitor.regulators import load_regulator_map, sources_from_regulators
from ts_monitor.sources import Source, load_catalog
from ts_monitor.weekday_scope import (
    ASEAN_MARKET_IDS,
    WEEKDAY_OFFICIAL_MARKET_IDS,
    include_in_weekday_run,
    weekday_fetch_catalog,
)

ROOT = Path(__file__).resolve().parents[1]

# Pollable URL counts from the live 28 November 2026 inventory.
EXPECTED_WEEKDAY_POLLABLE = {
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

# Identity of every inventory row, excluding the weekday_poll flag.
INVENTORY_IDENTITY_SHA256 = "cba2f0b611c0211e6df2225a0377ba1f504680175d9f203ea6fcdb82f731de28"
MARKETS_SHA256 = "274d0b885a26eda04cf8fc0ca276722484a5c774fac7cacc585296e67311101c"
REGULATIONS_SHA256 = "a189efe42d1e6ac3de399169cbf63e71c8af6df107f6117e583b04df02c1ad6b"
REGISTER_SHA256 = "2ff48fddc0475354b853b4df38bb94742d3553588ecd33a84c9a75f480cc2101"

EXCLUDED_MARKETS = ("gr", "no", "us-ca", "us-dc", "kp", "cn", "hk", "tw", "mo", "ae", "ru", "ir", "nz")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _inventory_identity(rows: list[dict]) -> str:
    identity = [
        (
            row["row_number"],
            row["market_id"],
            row["source_id"],
            row["url"],
            row["poll"],
            row["poll_tier"],
            row["status"],
        )
        for row in rows
    ]
    payload = json.dumps(identity, ensure_ascii=False).encode()
    return hashlib.sha256(payload).hexdigest()


def test_approved_markets_stay_weekday_pollable():
    inventory = load_official_inventory()
    assert len(inventory.rows) == 972
    assert WEEKDAY_OFFICIAL_MARKET_IDS == set(EXPECTED_WEEKDAY_POLLABLE)
    assert len(WEEKDAY_OFFICIAL_MARKET_IDS) == 29
    assert ASEAN_MARKET_IDS <= WEEKDAY_OFFICIAL_MARKET_IDS
    assert "kp" not in WEEKDAY_OFFICIAL_MARKET_IDS
    assert "gr" not in WEEKDAY_OFFICIAL_MARKET_IDS
    assert "no" not in WEEKDAY_OFFICIAL_MARKET_IDS
    assert "tl" not in WEEKDAY_OFFICIAL_MARKET_IDS
    assert not any(market_id.startswith("us-") for market_id in WEEKDAY_OFFICIAL_MARKET_IDS)

    for row in inventory.rows:
        assert row["weekday_poll"] is (row["market_id"] in WEEKDAY_OFFICIAL_MARKET_IDS)

    pollable = sources_for_poll(inventory)
    collected = sources_to_collect(inventory)
    assert [row["url"] for row in collected] == [source.url for source in pollable]
    counts: dict[str, int] = {}
    for source in pollable:
        assert source.jurisdiction in WEEKDAY_OFFICIAL_MARKET_IDS
        assert source.official is True
        assert source.auto_apply_eligible is False
        counts[source.jurisdiction or ""] = counts.get(source.jurisdiction or "", 0) + 1
    assert counts == EXPECTED_WEEKDAY_POLLABLE
    assert sum(counts.values()) == 364

    gb_rows = [row for row in inventory.rows if row["market_id"] == "gb"]
    assert len(gb_rows) == 25
    dsit = next(row for row in gb_rows if row["source_id"] == "gb-dsit")
    assert dsit["status"] == "retired"
    assert dsit["poll"] is False
    assert dsit["weekday_poll"] is True
    assert dsit["url"] not in {source.url for source in pollable}
    assert sum(1 for row in gb_rows if row["url"] in {source.url for source in pollable}) == 24

    federal = [row for row in inventory.rows if row["market_id"] == "us"]
    assert len(federal) == 16
    assert all(row["weekday_poll"] is True for row in federal)
    assert all(row["url"] in {source.url for source in pollable} for row in federal)


def test_greece_norway_and_us_states_are_not_weekday_polled():
    inventory = load_official_inventory()
    poll_urls = {source.url for source in sources_for_poll(inventory)}
    market_ids = {row["market_id"] for row in inventory.rows}
    assert "tl" not in market_ids
    for market_id in EXCLUDED_MARKETS:
        rows = [row for row in inventory.rows if row["market_id"] == market_id]
        assert rows, market_id
        assert all(row["weekday_poll"] is False for row in rows)
        assert all(row["url"] not in poll_urls for row in rows)
        assert all(row["url"] for row in rows)
    state_rows = [row for row in inventory.rows if row["market_id"].startswith("us-")]
    assert len(state_rows) > 50
    assert {row["market_id"] for row in state_rows} >= {"us-ca", "us-ny", "us-dc"}
    assert all(row["weekday_poll"] is False for row in state_rows)
    assert all(row["url"] not in poll_urls for row in state_rows)


def test_inventory_rows_and_score_files_are_unchanged():
    raw = json.loads((ROOT / "data" / "official_sources.json").read_text(encoding="utf-8"))
    rows = raw["sources"]
    assert len(rows) == 972
    assert raw["counts"]["rows"] == 972
    assert raw["counts"]["original"] == 671
    assert raw["counts"]["added"] == 301
    assert raw["counts"]["pollable"] == 364
    assert raw["counts"]["weekday_markets"] == 29
    assert _inventory_identity(rows) == INVENTORY_IDENTITY_SHA256
    assert _sha256(ROOT / "dashboard" / "data" / "markets.json") == MARKETS_SHA256
    assert _sha256(ROOT / "dashboard" / "data" / "regulations.json") == REGULATIONS_SHA256
    assert _sha256(ROOT / "data" / "register_snapshot.json") == REGISTER_SHA256


def test_weekday_run_catalogue_matches_the_approved_set_and_keeps_timor_leste():
    catalog = load_catalog(ROOT / "config" / "sources.yaml")
    reg_map = load_regulator_map(ROOT / "config" / "regulators.yaml")
    assert reg_map.counts()["bodies"] == 108
    assert reg_map.counts()["scrape_targets"] == 175
    assert reg_map.by_id("gr-parliament") is not None
    assert reg_map.by_id("cn-cac") is not None
    assert reg_map.by_id("ae-cabinet") is not None
    assert reg_map.by_id("us-ca-legislature") is not None
    assert catalog.by_id("us-ca-leginfo") is not None

    fetch = weekday_fetch_catalog(catalog, sources_from_regulators(reg_map))
    official = [source for source in fetch.sources if source.official]
    news = [source for source in fetch.sources if not source.official]
    codes = {(source.jurisdiction or "").upper() for source in official}
    assert "GR" not in codes
    assert "NO" not in codes
    assert "US-CA" not in codes
    assert "US-NY" not in codes
    assert "US-TX" not in codes
    assert "US-MN" not in codes
    assert "US-VA" not in codes
    assert "CN" not in codes
    assert "AE" not in codes
    assert {"US", "GB", "EU", "AU", "KR"} <= codes
    assert not any(code.startswith("US-") for code in codes)

    timor = [source for source in fetch.sources if (source.jurisdiction or "").upper() == "TL"]
    assert [source.id for source in timor] == ["tl-parliament-home"]
    assert timor[0].role == "legislative_record"
    assert timor[0].url == "https://www.parlamento.tl/"
    assert timor[0].official is True

    assert "us-ca-leginfo" not in {source.id for source in fetch.sources}
    assert "https://leginfo.legislature.ca.gov/" not in {source.url for source in fetch.sources}
    assert not any("hellenicparliament.gr" in source.url for source in fetch.sources)
    assert len(news) == 18
    assert len(official) == 173
    yaml_official = {source.id for source in catalog.sources if source.official and include_in_weekday_run(source)}
    assert len(yaml_official) == 31
    added = [source for source in official if source.id not in {item.id for item in catalog.sources}]
    assert len(added) == 142


def test_weekday_run_source_rules():
    def source(**overrides: object) -> Source:
        fields = {
            "id": "sample",
            "name": "Sample",
            "url": "https://example.test/official",
            "method": "html_index",
            "official": True,
            "auto_apply_eligible": False,
            "role": "instrument",
            "jurisdiction": "GR",
        }
        fields.update(overrides)
        return Source(**fields)

    assert include_in_weekday_run(source(jurisdiction="US"))
    assert include_in_weekday_run(source(jurisdiction="us"))
    assert include_in_weekday_run(source(jurisdiction="KR"))
    assert not include_in_weekday_run(source(jurisdiction="US-CA"))
    assert not include_in_weekday_run(source(jurisdiction="us-ny"))
    assert not include_in_weekday_run(source(jurisdiction="NO"))
    assert not include_in_weekday_run(source(jurisdiction="GR"))
    assert not include_in_weekday_run(source(jurisdiction="KP"))
    assert include_in_weekday_run(source(jurisdiction="TL", role="legislative_record"))
    assert not include_in_weekday_run(source(jurisdiction="TL", role="instrument"))
    assert include_in_weekday_run(source(official=False, jurisdiction="GR", role="news"))
    assert not include_in_weekday_run(source(jurisdiction=None))


def test_run_command_fetches_only_the_weekday_catalogue(monkeypatch, tmp_path: Path):
    captured: dict[str, object] = {}

    class FakeFetcher:
        def __init__(self, catalog) -> None:
            captured["jurisdictions"] = sorted(
                {(source.jurisdiction or "").upper() for source in catalog.sources if source.official}
            )
            captured["urls"] = [source.url for source in catalog.sources]
            self.errors: list = []

        def fetch_all(self, since: str | None = None, official_only: bool = False) -> list:
            captured["since"] = since
            captured["official_only"] = official_only
            return []

    def fake_pipeline(items, register, catalog, out_dir, errors=None):
        captured["match_urls"] = [source.url for source in catalog.sources]
        return []

    monkeypatch.setattr("ts_monitor.cli.Fetcher", FakeFetcher)
    monkeypatch.setattr("ts_monitor.cli.run_pipeline", fake_pipeline)
    code = main(["run", "--since", "2026-11-27", "--out", str(tmp_path)])
    assert code == 0
    jurisdictions = set(captured["jurisdictions"])
    urls = captured["urls"]
    match_urls = captured["match_urls"]
    assert isinstance(urls, list)
    assert isinstance(match_urls, list)
    assert "GR" not in jurisdictions
    assert "NO" not in jurisdictions
    assert "US-CA" not in jurisdictions
    assert "CN" not in jurisdictions
    assert "AE" not in jurisdictions
    assert "US" in jurisdictions
    assert "TL" in jurisdictions
    assert "https://www.parlamento.tl/" in urls
    assert "https://leginfo.legislature.ca.gov/" not in urls
    assert not any("hellenicparliament.gr" in url for url in urls)
    # The sourced Greece page stays available for matching and stays out of the fetch.
    assert any("hellenicparliament.gr" in url for url in match_urls)
    assert "https://leginfo.legislature.ca.gov/" in match_urls
    assert _sha256(ROOT / "dashboard" / "data" / "markets.json") == MARKETS_SHA256
    assert _sha256(ROOT / "dashboard" / "data" / "regulations.json") == REGULATIONS_SHA256
