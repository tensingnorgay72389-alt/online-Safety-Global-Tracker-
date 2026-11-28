"""Official intake must fetch international URLs and survive one bad candidate."""

from __future__ import annotations

import sys
from http.client import HTTPMessage

import pytest

from ts_monitor.official_intake import (
    PageFetch,
    _ascii_request_url,
    _default_fetch,
    collect_official,
)
import ts_monitor.official_intake as official_intake

RSS = """<?xml version="1.0"?>
<rss><channel><item>
<title>Later child safety bill</title>
<link>https://example.test/later</link>
<description>Age assurance duty for platforms</description>
</item></channel></rss>
"""
LANDING = """<html><body>
<a href="/news/raise-child-safety">Child safety notice</a>
<a href="/news/âge-assurance-update">Age assurance update</a>
<a href="/news/already%20encoded-guidance">Guidance note</a>
</body></html>
"""


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (
            "https://example.test/news/actualité",
            "https://example.test/news/actualit%C3%A9",
        ),
        (
            "https://example.test/news/actualit%C3%A9",
            "https://example.test/news/actualit%C3%A9",
        ),
        (
            "https://example.test/news/already%20encoded?q=a+b&x=1#section",
            "https://example.test/news/already%20encoded?q=a+b&x=1#section",
        ),
        (
            "https://example.test/a%2Fb/c",
            "https://example.test/a%2Fb/c",
        ),
        (
            "https://Example.COM/Path?Q=1#Frag",
            "https://Example.COM/Path?Q=1#Frag",
        ),
        (
            "https://example.test/search?q=儿童&ok=1&x=a+b",
            "https://example.test/search?q=%E5%84%BF%E7%AB%A5&ok=1&x=a+b",
        ),
        (
            "https://example.test/path?q=%E5%84%BF&raw=童",
            "https://example.test/path?q=%E5%84%BF&raw=%E7%AB%A5",
        ),
        (
            "https://example.test/doc?q=a%20b#第1节",
            "https://example.test/doc?q=a%20b#%E7%AC%AC1%E8%8A%82",
        ),
        (
            "https://example.test/caf%C3%A9/新闻",
            "https://example.test/caf%C3%A9/%E6%96%B0%E9%97%BB",
        ),
        (
            "https://münchen.example/caf%C3%A9?q=a%20b#résumé",
            "https://xn--mnchen-3ya.example/caf%C3%A9?q=a%20b#r%C3%A9sum%C3%A9",
        ),
        (
            "https://straße.de/straße",
            "https://strasse.de/stra%C3%9Fe",
        ),
        (
            "https://user:päss@münchen.example:8443/straße",
            "https://user:p%C3%A4ss@xn--mnchen-3ya.example:8443/stra%C3%9Fe",
        ),
        (
            "http://user:päss@[::1]:8080/新闻",
            "http://user:p%C3%A4ss@[::1]:8080/%E6%96%B0%E9%97%BB",
        ),
        (
            "https://xn--mnchen-3ya.example/新闻",
            "https://xn--mnchen-3ya.example/%E6%96%B0%E9%97%BB",
        ),
        (
            "http://[::1]/path",
            "http://[::1]/path",
        ),
    ],
)
def test_request_url_encodes_non_ascii_without_touching_encoded_parts(raw: str, expected: str):
    assert _ascii_request_url(raw) == expected
    assert expected.isascii()


class _Headers:
    def __init__(self, content_type: str) -> None:
        self._content_type = content_type

    def get_content_charset(self) -> str:
        return "utf-8"

    def get(self, name: str, default: str | None = None) -> str | None:
        if name.lower() == "content-type":
            return self._content_type
        return default


class _Response:
    def __init__(self, url: str, body: str, content_type: str) -> None:
        self.status = 200
        self.headers = _Headers(content_type)
        self._body = body.encode("utf-8")
        self._url = url

    def read(self) -> bytes:
        return self._body

    def geturl(self) -> str:
        return self._url

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *args: object) -> bool:
        return False


def test_default_fetch_sends_percent_encoded_and_idn_urls(monkeypatch: pytest.MonkeyPatch):
    opened: list[str] = []

    def fake_urlopen(request, timeout=None):
        url = request.full_url
        opened.append(url)
        assert url.isascii()
        if any(ord(char) > 127 for char in url):
            raise UnicodeEncodeError("ascii", url, 0, 1, "ordinal not in range(128)")
        return _Response(url, "<html><title>Fetched</title></html>", "text/html")

    monkeypatch.setattr(official_intake, "urlopen", fake_urlopen)
    encoded = _default_fetch("https://münchen.example/actualité?q=儿童#节")
    unchanged = _default_fetch("https://example.test/news/actualit%C3%A9?q=a%20b&x=1#section")
    assert encoded.error is None
    assert encoded.status == 200
    assert unchanged.error is None
    assert opened == [
        "https://xn--mnchen-3ya.example/actualit%C3%A9?q=%E5%84%BF%E7%AB%A5#%E8%8A%82",
        "https://example.test/news/actualit%C3%A9?q=a%20b&x=1#section",
    ]


def test_encoding_and_invalid_url_failures_are_recorded(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]):
    def fail_if_opened(request, timeout=None):
        raise UnicodeEncodeError("ascii", request.full_url, 16, 22, "ordinal not in range(128)")

    monkeypatch.setattr(official_intake, "urlopen", fail_if_opened)
    bad_host = "https://a..bücher.example/news?api_key=test-not-a-real-secret&q=1"
    host_page = _default_fetch(bad_host)
    assert host_page.error == "encoding"
    assert host_page.status is None
    assert host_page.url == bad_host

    encode_page = _default_fetch("https://example.test/raise-encode")
    assert encode_page.error == "encoding"
    assert encode_page.url == "https://example.test/raise-encode"

    surrogate = _default_fetch("https://example.test/\ud800news")
    assert surrogate.error == "encoding"
    assert surrogate.url == "https://example.test/\ud800news"

    logged = capsys.readouterr().err
    assert "official fetch encoding error for https://a..bücher.example/news?api_key=***&q=1" in logged
    assert "test-not-a-real-secret" not in logged
    assert "label empty or too long" in logged
    assert "official fetch encoding error for https://example.test/raise-encode" in logged
    assert "position 16-21" in logged


def test_invalid_url_is_recorded_without_logging_secrets(capsys: pytest.CaptureFixture[str]):
    secret_url = "https://user:test-not-a-real-password@example.test/a b?api_key=test-not-a-real-secret&q=1"
    page = _default_fetch(secret_url)
    assert page.error == "invalid_url"
    assert page.url == secret_url
    logged = capsys.readouterr().err
    assert "official fetch invalid_url error for https://user:***@example.test/a b?api_key=***&q=1" in logged
    assert "test-not-a-real-password" not in logged
    assert "test-not-a-real-secret" not in logged

    ipv6 = _default_fetch("http://[")
    assert ipv6.error == "invalid_url"
    assert ipv6.url == "http://["


class _HeaderResponse:
    """Response whose charset is parsed from a real Content-Type header."""

    def __init__(self, url: str, body: bytes, content_type: str) -> None:
        self.status = 200
        self.headers = HTTPMessage()
        self.headers["Content-Type"] = content_type
        self._body = body
        self._url = url

    def read(self) -> bytes:
        return self._body

    def geturl(self) -> str:
        return self._url

    def __enter__(self) -> _HeaderResponse:
        return self

    def __exit__(self, *args: object) -> bool:
        return False


@pytest.mark.parametrize(
    ("content_type", "charset"),
    [
        ("text/html; charset=utf-8,gbk", "utf-8,gbk"),
        ('text/html; charset="utf-8,gbk"', "utf-8,gbk"),
        ("text/html; charset=x-not-a-charset", "x-not-a-charset"),
    ],
)
def test_unknown_charset_is_recorded(
    content_type: str,
    charset: str,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
):
    def fake_urlopen(request, timeout=None):
        return _HeaderResponse(request.full_url, b"<html><title>Notice</title></html>", content_type)

    monkeypatch.setattr(official_intake, "urlopen", fake_urlopen)
    url = "https://example.test/mixed-charset?api_key=test-not-a-real-secret"
    page = _default_fetch(url)
    assert page.error == "encoding"
    assert page.status is None
    assert page.body == ""
    assert page.url == url
    logged = capsys.readouterr().err
    expected = (
        "official fetch encoding error for "
        f"https://example.test/mixed-charset?api_key=***: unknown encoding: {charset}"
    )
    assert expected in logged
    assert "test-not-a-real-secret" not in logged


def test_known_gbk_charset_still_decodes(monkeypatch: pytest.MonkeyPatch):
    def fake_urlopen(request, timeout=None):
        return _HeaderResponse(request.full_url, "儿童安全".encode("gbk"), "text/html; charset=gbk")

    monkeypatch.setattr(official_intake, "urlopen", fake_urlopen)
    page = _default_fetch("https://example.test/gbk")
    assert page.error is None
    assert page.status == 200
    assert "儿童安全" in page.body


def test_unknown_charset_does_not_abort_remaining_sources(monkeypatch: pytest.MonkeyPatch):
    opened: list[str] = []

    def fake_urlopen(request, timeout=None):
        url = request.full_url
        opened.append(url)
        if url.endswith("/mixed-charset"):
            return _HeaderResponse(url, b"<html><title>Bad charset</title></html>", "text/html; charset=utf-8,gbk")
        if url.endswith("/after.xml"):
            return _Response(url, RSS, "application/rss+xml")
        raise AssertionError(f"unexpected fetch {url}")

    monkeypatch.setattr(official_intake, "urlopen", fake_urlopen)
    articles, errors = collect_official(
        [
            {
                "source_id": "mixed",
                "source_name": "Mixed charset",
                "url": "https://example.test/mixed-charset",
                "adapter": "html-list",
                "verification_status": "verified",
            },
            {
                "source_id": "after",
                "source_name": "After",
                "url": "https://example.test/after.xml",
                "adapter": "rss",
                "verification_status": "verified",
            },
        ]
    )
    assert opened == [
        "https://example.test/mixed-charset",
        "https://example.test/after.xml",
    ]
    assert [article["title"] for article in articles] == ["Later child safety bill"]
    assert errors == [
        {
            "source_id": "mixed",
            "url": "https://example.test/mixed-charset",
            "status": None,
            "error": "encoding",
            "verification_status": "verified",
            "dead": False,
        }
    ]


def test_encoding_error_log_survives_an_ascii_stderr(monkeypatch: pytest.MonkeyPatch):
    class StrictASCII:
        def __init__(self) -> None:
            self.chunks: list[str] = []

        def write(self, text: str) -> int:
            text.encode("ascii")
            self.chunks.append(text)
            return len(text)

        def flush(self) -> None:
            return None

    stream = StrictASCII()
    monkeypatch.setattr(sys, "stderr", stream)
    page = _default_fetch("https://a..bücher.example/news")
    assert page.error == "encoding"
    logged = "".join(stream.chunks)
    assert "official fetch encoding error" in logged
    assert "\\xfc" in logged
    assert "bücher" not in logged


def test_official_collection_continues_after_one_bad_url(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]):
    opened: list[str] = []

    def fake_urlopen(request, timeout=None):
        url = request.full_url
        opened.append(url)
        if not url.isascii():
            raise UnicodeEncodeError("ascii", url, 16, 22, "ordinal not in range(128)")
        if url.endswith("/raise-encode") or url.endswith("/raise-child-safety"):
            raise UnicodeEncodeError("ascii", url, 16, 22, "ordinal not in range(128)")
        if url.endswith("/landing"):
            return _Response(url, LANDING, "text/html")
        if url.endswith("/%C3%A2ge-assurance-update"):
            return _Response(url, "<html><title>Age assurance update</title></html>", "text/html")
        if "already%20encoded-guidance" in url:
            assert "already%2520encoded" not in url
            return _Response(url, "<html><title>Encoded guidance</title></html>", "text/html")
        if url.endswith("/after.xml"):
            return _Response(url, RSS, "application/rss+xml")
        raise AssertionError(f"unexpected fetch {url}")

    monkeypatch.setattr(official_intake, "urlopen", fake_urlopen)
    bad_host = "https://a..bücher.example/news?token=test-not-a-real-secret"
    rows = [
        {
            "source_id": "landing",
            "source_name": "Landing",
            "url": "https://example.test/landing",
            "adapter": "html-list",
            "verification_status": "verified",
        },
        {
            "source_id": "bad-host",
            "source_name": "Bad host",
            "url": bad_host,
            "adapter": "html-list",
            "verification_status": "verified",
        },
        {
            "source_id": "encode",
            "source_name": "Encode",
            "url": "https://example.test/raise-encode",
            "adapter": "html-list",
            "verification_status": "unverified",
        },
        {
            "source_id": "after",
            "source_name": "After",
            "url": "https://example.test/after.xml",
            "adapter": "rss",
            "verification_status": "verified",
        },
    ]
    articles, errors = collect_official(rows)
    assert opened == [
        "https://example.test/landing",
        "https://example.test/news/raise-child-safety",
        "https://example.test/news/%C3%A2ge-assurance-update",
        "https://example.test/news/already%20encoded-guidance",
        "https://example.test/raise-encode",
        "https://example.test/after.xml",
    ]
    assert [article["title"] for article in articles] == [
        "Age assurance update",
        "Encoded guidance",
        "Later child safety bill",
    ]
    assert [row["url"] for row in errors] == [
        "https://example.test/news/raise-child-safety",
        bad_host,
        "https://example.test/raise-encode",
    ]
    assert {row["error"] for row in errors} == {"encoding"}
    assert all(row["dead"] is False and row["status"] is None for row in errors)
    assert errors[0]["source_id"] == "landing"
    assert errors[1]["source_id"] == "bad-host"
    assert errors[2]["verification_status"] == "unverified"
    logged = capsys.readouterr().err
    assert bad_host.split("?", 1)[0] in logged
    assert "token=***" in logged
    assert "test-not-a-real-secret" not in logged
    assert "https://example.test/raise-encode" in logged


def test_raising_fetcher_does_not_abort_the_remaining_sources():
    def getter(url: str) -> PageFetch:
        if url.endswith("/bad"):
            raise UnicodeEncodeError("ascii", "https://example.test/actualité", 16, 22, "ordinal not in range(128)")
        return PageFetch(url, 200, RSS, "application/rss+xml", url)

    articles, errors = collect_official(
        [
            {"source_id": "bad", "source_name": "Bad", "url": "https://example.test/bad", "adapter": "rss", "verification_status": "verified"},
            {"source_id": "good", "source_name": "Good", "url": "https://example.test/good.xml", "adapter": "rss", "verification_status": "verified"},
        ],
        getter,
    )
    assert errors[0]["error"] == "encoding"
    assert errors[0]["url"] == "https://example.test/bad"
    assert errors[0]["dead"] is False
    assert [article["title"] for article in articles] == ["Later child safety bill"]
