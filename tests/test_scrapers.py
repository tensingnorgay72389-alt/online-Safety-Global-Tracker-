from __future__ import annotations

from pathlib import Path

from ts_monitor.fetchers import Fetcher
from ts_monitor.parsers import parse_official_bill_html
from ts_monitor.scrapers import extract_named_officials, parse_newsroom_html
from ts_monitor.sources import FetchSettings, Source, SourceCatalog

ROOT = Path(__file__).resolve().parents[1]
HTML = ROOT / "tests" / "fixtures" / "html"


def test_parse_regulator_newsroom_fixture():
    html = (HTML / "ftc_newsroom.html").read_text(encoding="utf-8")
    rows = parse_newsroom_html(html, "https://www.ftc.gov/news-events")
    headlines = [row["headline"] for row in rows]
    assert "FTC announces a COPPA compliance update" in headlines
    first = next(row for row in rows if "COPPA" in row["headline"])
    assert first["url"].endswith("ftc-announces-coppa-compliance-update")
    assert first["published_date"] == "2026-11-20"


def test_parse_ministry_media_release_index_fixture():
    html = (HTML / "heritage_media_releases.html").read_text(encoding="utf-8")
    rows = parse_newsroom_html(
        html, "https://www.canada.ca/en/canadian-heritage/news.html"
    )
    headlines = [row["headline"] for row in rows]
    assert "Minister announces the next step on the Safe Social Media Act" in headlines
    first = next(row for row in rows if "Safe Social Media Act" in row["headline"])
    assert first["published_date"] == "2026-11-18"
    assert "safe-social-media-act-update" in first["url"]


def test_bill_homepage_fixture_is_passed_without_assent():
    html = (HTML / "audoc_bill_homepage.html").read_text(encoding="utf-8")
    parsed = parse_official_bill_html(html)
    assert parsed.get("raw_status_text") and "Passed Both Houses" in parsed["raw_status_text"]
    assert parsed.get("raw_assent_listed") is False


def test_missing_spokesperson_page_returns_no_named_officials():
    html = (HTML / "missing_spokesperson.html").read_text(encoding="utf-8")
    found = extract_named_officials(html)
    assert found == []


def test_fetch_source_newsroom_and_official_page_with_stubbed_http():
    newsroom = Source(
        id="test-newsroom",
        name="Example newsroom",
        url="https://example.invalid/news",
        method="newsroom",
        official=True,
        auto_apply_eligible=True,
        role="regulator_newsroom",
        jurisdiction="US",
    )
    releases = Source(
        id="test-releases",
        name="Example ministry releases",
        url="https://example.invalid/media-releases",
        method="media_release_index",
        official=True,
        auto_apply_eligible=False,
        role="ministerial_release",
        jurisdiction="CA",
    )
    bill = Source(
        id="test-bill",
        name="Official bill homepage",
        url="https://example.invalid/bill",
        method="official_page",
        official=True,
        auto_apply_eligible=True,
        role="instrument",
        jurisdiction="AU",
    )
    catalog = SourceCatalog(sources=[newsroom, releases, bill], fetch=FetchSettings())
    pages = {
        newsroom.url: (HTML / "ftc_newsroom.html").read_text(encoding="utf-8"),
        releases.url: (HTML / "heritage_media_releases.html").read_text(encoding="utf-8"),
        bill.url: (HTML / "audoc_bill_homepage.html").read_text(encoding="utf-8"),
    }

    def opener(url, user_agent, timeout):
        assert user_agent
        assert timeout >= 1
        return 200, pages[url], url

    fetcher = Fetcher(catalog=catalog, opener=opener)
    news_items = fetcher.fetch_source(newsroom, since="2026-11-01")
    assert any("COPPA" in item.headline for item in news_items)
    assert all((item.published_date or "2026-11-01") >= "2026-11-01" for item in news_items)
    release_items = fetcher.fetch_source(releases, since="2026-01-01")
    assert any("Safe Social Media Act" in item.headline for item in release_items)
    assert all(item.source_kind == "ministerial_release" for item in release_items)
    bill_items = fetcher.fetch_source(bill)
    assert bill_items[0].raw_status_text and "Passed Both Houses" in bill_items[0].raw_status_text
    assert bill_items[0].raw_assent_listed is False
