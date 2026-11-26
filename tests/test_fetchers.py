from __future__ import annotations

from urllib.error import HTTPError, URLError
from io import BytesIO

from ts_monitor.fetchers import Fetcher
from ts_monitor.sources import Source, SourceCatalog, FetchSettings


def _catalog(url: str, method: str = "official_page") -> tuple[SourceCatalog, Source]:
    source = Source(
        id="test-source",
        name="Test official page",
        url=url,
        method=method,
        official=True,
        auto_apply_eligible=True,
        role="instrument",
        jurisdiction="AU",
    )
    return SourceCatalog(sources=[source], fetch=FetchSettings(timeout_seconds=2)), source


def test_403_is_recorded_and_not_treated_as_missing(tmp_path):
    catalog, source = _catalog("https://example.invalid/bill")

    def opener(url, user_agent, timeout):
        raise HTTPError(url, 403, "Forbidden", hdrs=None, fp=BytesIO())

    fetcher = Fetcher(catalog=catalog, opener=opener)
    items = fetcher.fetch_source(source)
    assert items == []
    assert len(fetcher.errors) == 1
    error = fetcher.errors[0]
    assert error.error_type == "http_403"
    assert error.status_code == 403
    assert "not treated as evidence that the page does not exist" in error.note


def test_timeout_is_recorded(tmp_path):
    catalog, source = _catalog("https://example.invalid/bill")

    def opener(url, user_agent, timeout):
        raise URLError("timed out")

    fetcher = Fetcher(catalog=catalog, opener=opener)
    items = fetcher.fetch_source(source)
    assert items == []
    assert fetcher.errors[0].error_type == "timeout"
    assert "not treated as evidence that the page does not exist" in fetcher.errors[0].note


def test_rss_and_official_page_parse_with_stubbed_http():
    rss_source = Source(
        id="news-bbc-test",
        name="BBC News",
        url="https://example.invalid/rss.xml",
        method="rss",
        official=False,
        auto_apply_eligible=False,
        role="news",
    )
    official = Source(
        id="au-page-test",
        name="Official bill homepage",
        url="https://example.invalid/bill",
        method="official_page",
        official=True,
        auto_apply_eligible=True,
        role="instrument",
        jurisdiction="AU",
    )
    catalog = SourceCatalog(sources=[rss_source, official], fetch=FetchSettings())
    rss = """<?xml version="1.0"?>
    <rss version="2.0"><channel>
      <title>Example</title>
      <item>
        <title>Example online safety bill update</title>
        <link>https://example.invalid/story</link>
        <pubDate>Tue, 25 Nov 2026 10:00:00 GMT</pubDate>
        <description>A discovery-only news item.</description>
      </item>
    </channel></rss>
    """
    html = "<html><body><p>Status: Passed Both Houses</p><p>Royal Assent is not listed.</p></body></html>"

    def opener(url, user_agent, timeout):
        if url.endswith("rss.xml"):
            return 200, rss, url
        return 200, html, url

    fetcher = Fetcher(catalog=catalog, opener=opener)
    news_items = fetcher.fetch_source(rss_source, since="2026-11-01")
    assert len(news_items) == 1
    assert news_items[0].headline.startswith("Example online safety")
    official_items = fetcher.fetch_source(official)
    assert official_items[0].raw_status_text and "Passed Both Houses" in official_items[0].raw_status_text
    assert official_items[0].raw_assent_listed is False
