from __future__ import annotations

import json
from pathlib import Path

from ts_monitor.cli import main
from ts_monitor.regulators import (
    ALLOWED_BODY_TYPES,
    load_regulator_map,
    merge_source_catalog,
    sources_from_regulators,
)
from ts_monitor.sources import FetchSettings, Source, SourceCatalog

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"
SAMPLE = FIXTURES / "regulators" / "sample_map.yaml"


def test_live_map_loads_with_sourced_spokespersons_only():
    reg_map = load_regulator_map(ROOT / "config" / "regulators.yaml")
    counts = reg_map.counts()
    assert counts["bodies"] == 108
    assert counts["spokespersons"] == 28
    assert counts["personal_handles"] == 2
    assert counts["institutional_handles"] == 5
    assert counts["scrape_targets"] == 175
    assert len({body.id for body in reg_map.bodies}) == 108
    for body in reg_map.bodies:
        assert body.body_type in ALLOWED_BODY_TYPES
        for person in body.spokespersons:
            assert person.name
            assert person.role
            assert person.source_url.startswith("http")
            if person.x_handle:
                assert person.x_handle_status == "listed_on_official_page"
                assert person.x_handle_url
    # Ministerial scrape targets must not be auto-applied, even if a YAML flag is loose.
    for source in sources_from_regulators(reg_map):
        if source.role == "ministerial_release":
            assert source.auto_apply_eligible is False


def test_sample_map_strips_unverified_handles_and_keeps_missing_spokesperson_empty():
    reg_map = load_regulator_map(SAMPLE)
    chair = reg_map.by_id("test-regulator").spokespersons[0]
    assert chair.name == "Jane Example"
    assert chair.x_handle == "JaneExampleOfficial"
    minister = reg_map.by_id("test-ministry").spokespersons[0]
    assert minister.name == "Unverified Person"
    assert minister.x_handle is None
    assert minister.x_handle_url is None
    assert minister.x_handle_status == "unverified"
    missing = reg_map.by_id("test-missing-spokesperson")
    assert missing.spokespersons == []
    assert missing.spokesperson_status == "no_named_official_on_retrieved_page"


def test_ministerial_source_is_never_auto_apply_eligible():
    sources = sources_from_regulators(load_regulator_map(SAMPLE))
    by_id = {source.id: source for source in sources}
    assert by_id["test-ministry-releases"].role == "ministerial_release"
    assert by_id["test-ministry-releases"].auto_apply_eligible is False
    assert by_id["test-regulator-news"].auto_apply_eligible is True


def test_merge_source_catalog_deduplicates_by_host_and_path():
    existing = Source(
        id="already-there",
        name="Existing",
        url="https://www.example.invalid/regulator/news",
        method="html_index",
        official=True,
        auto_apply_eligible=True,
        role="regulator_newsroom",
    )
    catalog = SourceCatalog(sources=[existing], fetch=FetchSettings())
    extras = sources_from_regulators(load_regulator_map(SAMPLE))
    merged = merge_source_catalog(catalog, extras)
    urls = [source.url for source in merged.sources]
    assert urls.count("https://example.invalid/regulator/news") == 0 or urls.count(
        "https://www.example.invalid/regulator/news"
    ) == 1
    # The www-prefixed existing source should suppress the map's same host and path.
    assert [source.id for source in merged.sources].count("test-regulator-news") == 0
    assert "test-ministry-releases" in {source.id for source in merged.sources}


def test_regulators_cli_json(capsys):
    code = main(["regulators", "--json", "--regulators", str(SAMPLE)])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["counts"]["bodies"] == 3
    assert payload["counts"]["spokespersons"] == 2
    assert payload["counts"]["personal_handles"] == 1
    missing = next(body for body in payload["bodies"] if body["id"] == "test-missing-spokesperson")
    assert missing["spokespersons"] == []


def test_legislative_record_sources_are_never_auto_apply_eligible():
    from ts_monitor.regulators import load_regulator_map, sources_from_regulators

    sources = sources_from_regulators(load_regulator_map(ROOT / "config" / "regulators.yaml"))
    records = [source for source in sources if source.role == "legislative_record"]
    assert records
    assert all(source.auto_apply_eligible is False for source in records)
    assert all(source.official is True for source in records)


def test_mcmc_india_and_asean_official_targets_are_mapped():
    from ts_monitor.regulators import load_regulator_map

    reg_map = load_regulator_map(ROOT / "config" / "regulators.yaml")
    mcmc_urls = {target.url for target in reg_map.by_id("my-mcmc").scrape_targets}
    assert "https://www.mcmc.gov.my/en/media/press-releases" in mcmc_urls
    assert "https://www.mcmc.gov.my/en/media/announcements" in mcmc_urls
    assert "https://www.mcmc.gov.my/en/onsa/resources/public-consultation" in mcmc_urls
    assert reg_map.by_id("my-komunikasi") is not None
    assert reg_map.by_id("in-trai").spokespersons[0].name == "Anil Kumar Lahoti"
    assert reg_map.by_id("in-mib").spokespersons[0].name == "Ashwini Vaishnaw"
    assert any(target.url.endswith("/ls/legislation/bills") for target in reg_map.by_id("in-parliament").scrape_targets)
    asean = {"BN", "KH", "ID", "LA", "MY", "MM", "PH", "SG", "TH", "VN"}
    present = {body.jurisdiction for body in reg_map.bodies}
    assert asean <= present
    assert "TL" in present
    assert reg_map.by_id("us-house") is not None
    assert reg_map.by_id("eu-parliament") is not None


def test_readme_includes_live_tracker_link():
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "https://cursor.com/canvas/store-ebf3ffb9-7e41-4683-935a-adf799982e56/6246d529-8c4f-4535-9f6a-670da7b635fa" in text
    assert "Live tracker" in text or "live tracker" in text
    # The vocabulary dashboard is not this tracker. The README no longer links it.
    assert "patriciayyzhai.github.io/global-trust-safety-dashboard" not in text
