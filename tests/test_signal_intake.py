from __future__ import annotations

import json
from pathlib import Path

import pytest

from ts_monitor.cli import main
from ts_monitor.dedup import deduplicate
from ts_monitor.gnews import GNEWS_SEARCH_URL, fetch_gnews, resolve_gnews_key
from ts_monitor.official_intake import PageFetch, collect_official, sources_to_collect
from ts_monitor.official_inventory import load_official_inventory
from ts_monitor.signal_routing import assert_review_output, route_record, write_review_queue
from ts_monitor.signal_weights import actor_weight
from ts_monitor.xai_classifier import XaiClassifier, normalize_regulation_status

ROOT = Path(__file__).resolve().parents[1]
RSS = """<?xml version="1.0"?>
<rss><channel><item>
<title>Child safety bill</title>
<link>https://example.test/bill</link>
<description>Age assurance duty for platforms</description>
</item></channel></rss>
"""
LANDING = """<html><head>
<link rel="alternate" type="application/rss+xml" href="/feed.xml" />
</head><body>
<a href="/news/age-assurance-update">Age assurance update</a>
</body></html>
"""


def test_actor_weights_follow_the_scale():
    assert actor_weight("minister", False) == 0.90
    assert actor_weight("head of government or president", False) == 0.90
    assert actor_weight("deputy minister", False, speaking_as_department=True) == 0.90
    assert actor_weight("deputy minister", True, speaking_as_department=False) == 0.65
    assert actor_weight("deputy minister", False, speaking_as_department=False) == 0.50
    assert actor_weight("us state governor", True) == 0.65
    assert actor_weight("attorney general", False) == 0.50
    assert actor_weight("ngo or civil society organisation", True) == 0.25
    assert actor_weight("senate president", True) == 0.65


def test_confidence_gates_queue_review_and_do_not_apply():
    high = route_record({"action_type": "signal", "confidence": 0.91, "is_signal": True, "title": "A"})
    assert high is not None
    assert high["destination"] == "signals"
    assert high["urgent"] is True
    assert high["auto_applied"] is False
    assert high["written_to_register"] is False

    review = route_record({"action_type": "signal", "confidence": 0.62, "is_signal": True})
    assert review is not None and review["destination"] == "review" and review["urgent"] is False

    assert route_record({"action_type": "signal", "confidence": 0.49, "is_signal": True}) is None

    unmatched = route_record(
        {
            "action_type": "existing_regulation_development",
            "confidence": 0.8,
            "matched_regulation_id": "",
            "is_signal": False,
        }
    )
    assert unmatched is not None
    assert unmatched["destination"] == "review"
    assert unmatched["needs_match"] is True
    assert unmatched["auto_applied"] is False

    with pytest.raises(RuntimeError):
        assert_review_output(Path("regulations.json"))


def test_blocked_official_urls_are_attempted_and_not_marked_dead():
    calls: list[str] = []

    def getter(url: str) -> PageFetch:
        calls.append(url)
        if url.endswith("/blocked"):
            return PageFetch(url, 403, error="http_403")
        if url.endswith("/feed.xml"):
            return PageFetch(url, 200, RSS, "application/rss+xml", url)
        return PageFetch(url, 200, LANDING, "text/html", url)

    rows = [
        {"source_id": "feed", "source_name": "Feed", "url": "https://example.test/feed.xml", "adapter": "rss", "verification_status": "verified"},
        {"source_id": "blocked", "source_name": "Blocked", "url": "https://example.test/blocked", "adapter": "html-list", "verification_status": "unverified-blocked"},
        {"source_id": "landing", "source_name": "Landing", "url": "https://example.test/landing", "adapter": "html-list", "verification_status": "unverified"},
    ]
    articles, errors = collect_official(rows, getter)
    assert "https://example.test/blocked" in calls
    blocked = next(row for row in errors if row["status"] == 403)
    assert blocked["dead"] is False
    assert any(article["title"] == "Child safety bill" for article in articles)
    plan = sources_to_collect(load_official_inventory())
    assert len(plan) > 20
    assert any(row["market_id"] == "mx" for row in plan)
    assert any(row["market_id"] == "tr" for row in plan)
    assert any(row["verification_status"] == "unverified-blocked" for row in plan)


def test_gnews_uses_only_the_gnews_endpoint(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("NEWS_API_KEY", "legacy-not-a-real-key")
    monkeypatch.setenv("GNEWS_API_KEY", "gnews-not-a-real-key")
    monkeypatch.setenv("NEWS_API_KEY_FREE", "free-not-a-real-key")
    assert resolve_gnews_key()[0] == "NEWS_API_KEY_FREE"
    calls: list[tuple[str, str]] = []

    def transport(url: str, params: dict[str, str]) -> dict:
        calls.append((url, params["q"]))
        assert params["apikey"] == "free-not-a-real-key"
        assert "newsapi.org" not in url
        if params["q"] == "age assurance":
            raise OSError("gnews failed")
        return {
            "articles": [
                {
                    "title": "Platform duty",
                    "url": "https://example.com/reuters",
                    "description": "A regulator statement",
                    "publishedAt": "2026-11-01T00:00:00Z",
                    "source": {"name": "Reuters"},
                },
                {
                    "title": "Blog post",
                    "url": "https://example.com/blog",
                    "description": "Ignore",
                    "publishedAt": "2026-11-01T00:00:00Z",
                    "source": {"name": "Random Blog"},
                },
            ]
        }

    articles = fetch_gnews(transport)
    assert calls[0][0] == GNEWS_SEARCH_URL
    assert articles
    assert {article["source"]["name"] for article in articles} == {"Reuters"}

    monkeypatch.delenv("NEWS_API_KEY_FREE")
    monkeypatch.delenv("GNEWS_API_KEY")
    monkeypatch.delenv("NEWS_API_KEY")
    assert fetch_gnews(transport) == []


def test_dedup_uses_url_and_title_similarity():
    seen = {"urls": {"https://example.com/old": {"url": "https://example.com/old"}}, "titles": ["Ministers announce a child safety duty"]}
    articles = [
        {"title": "Ministers announce a child safety duty", "url": "https://example.com/new"},
        {"title": "Different gaming harm bill", "url": "https://example.com/old"},
        {"title": "Different gaming harm bill", "url": "https://example.com/gaming"},
    ]
    unique = deduplicate(articles, seen)
    assert [row["url"] for row in unique] == ["https://example.com/gaming"]


def test_classifier_uses_xai_schema_and_limits_snippets(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("XAI_API_KEY", "test-not-a-real-key")
    seen: list[dict] = []

    def transport(payload: dict) -> dict:
        seen.append(payload)
        assert payload["model"] == "grok-4.7"
        assert payload["temperature"] == 0.1
        name = payload["response_format"]["json_schema"]["name"]
        if name == "stage1_result":
            user = payload["messages"][1]["content"]
            assert "SNIPPET-TAIL" not in user
            body = {"is_regulatory": True, "reasoning": "Official statement"}
        elif name == "stage2_result":
            user = payload["messages"][1]["content"]
            assert "https://example.com/item" in user
            assert "STAGE2-TAIL" not in user
            body = {
                "action_type": "existing_regulation_report",
                "confidence": 0.4,
                "reasoning": "Statement rather than a bill",
                "regulation_name": None,
                "jurisdiction": "mx",
                "status_change": "preliminary findings",
                "summary": "A minister spoke about child safety",
                "matched_regulation_id": None,
            }
        else:
            body = {
                "is_signal": True,
                "confidence": 0.88,
                "reasoning": "Attributed minister statement",
                "actor_name": "Example Minister",
                "office": "Minister",
                "actor_class": "minister",
                "market_id": "mx",
                "specific_risk_or_mechanism": True,
                "speaking_as_department": True,
                "issue_or_focus": "child safety",
                "summary": "The minister named a duty of care",
            }
        return {"choices": [{"message": {"content": json.dumps(body)}}]}

    classifier = XaiClassifier(transport=transport)
    long_snippet = ("a" * 600) + "SNIPPET-TAIL" + ("b" * 600) + "STAGE2-TAIL"
    result = classifier.classify(
        {
            "title": "Minister statement",
            "description": long_snippet,
            "url": "https://example.com/item",
            "publishedAt": "2026-11-20",
            "source": {"name": "Official"},
        },
        "No existing regulations in database.",
    )
    assert result is not None
    assert result["action_type"] == "signal"
    assert result["confidence"] == 0.88
    assert result["actor_weight"] == 0.90
    assert result["status_change"] == "under_review"
    assert result["is_signal"] is True
    assert normalize_regulation_status("not a real status") is None


def test_intake_file_does_not_change_live_scores(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("XAI_API_KEY", raising=False)
    regulations = (ROOT / "dashboard" / "data" / "regulations.json").read_bytes()
    markets = (ROOT / "dashboard" / "data" / "markets.json").read_bytes()
    news = (ROOT / "dashboard" / "data" / "news_items.json").read_bytes()
    article_file = tmp_path / "articles.json"
    article_file.write_text(
        json.dumps([{"title": "Queued item", "url": "https://example.com/queued", "description": "Child safety"}]),
        encoding="utf-8",
    )
    code = main(
        [
            "intake",
            "--file",
            str(article_file),
            "--out",
            str(tmp_path / "out"),
            "--seen",
            str(tmp_path / "seen.json"),
            "--skip-classify",
        ]
    )
    assert code == 0
    assert (ROOT / "dashboard" / "data" / "regulations.json").read_bytes() == regulations
    assert (ROOT / "dashboard" / "data" / "markets.json").read_bytes() == markets
    assert (ROOT / "dashboard" / "data" / "news_items.json").read_bytes() == news
    queue = json.loads((tmp_path / "out" / "signals" / "review_queue.json").read_text(encoding="utf-8"))
    assert queue["signals"] == []
    assert "regulations" in queue["note"]
    write_review_queue(tmp_path / "signal_review.json", [], discarded=1)
