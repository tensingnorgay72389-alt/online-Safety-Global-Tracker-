"""Secondary news intake through GNews only.

Official pages stay primary. This module never calls NewsAPI.org.
The key is read from NEWS_API_KEY_FREE, then GNEWS_API_KEY, then NEWS_API_KEY.
A missing key or a failed request returns no articles and does not stop official intake.
The key is never logged.
"""

from __future__ import annotations

import json
import os
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

GNEWS_SEARCH_URL = "https://gnews.io/api/v4/search"
GNEWS_KEY_ENV_VARS = ("NEWS_API_KEY_FREE", "GNEWS_API_KEY", "NEWS_API_KEY")

# Patricia Zhai's trusted-outlet list. No outlet is added without a comparable public record.
TRUSTED_NEWS_SOURCES = (
    "Reuters",
    "Associated Press",
    "AP News",
    "BBC News",
    "Bloomberg",
    "Financial Times",
    "The Guardian",
    "The New York Times",
    "The Wall Street Journal",
    "Politico",
    "Agence France-Presse",
    "AFP",
    "Nikkei Asia",
    "The Globe and Mail",
)

# The first eight queries are her original English age-assurance set.
# The rest cover the wider topic inventory for this monitor.
GNEWS_KEYWORD_SETS = (
    "age assurance",
    "age verification social media",
    "underage social media ban",
    "online safety children regulation",
    "child online protection law",
    "age estimation platform",
    "minor online safety act",
    "kids online safety act",
    "under-16 social media ban",
    "child sexual abuse material platform regulation",
    "deepfake intimate image law",
    "platform duty of care online safety",
    "gaming harm children regulation",
    "AI companion chatbot child safety",
    "minister online safety statement",
    "school incident social media government response",
)


def resolve_gnews_key() -> tuple[str, str]:
    """Return (env var name, key). Both are empty when no key is configured."""
    for name in GNEWS_KEY_ENV_VARS:
        value = os.environ.get(name, "").strip()
        if value:
            return name, value
    return "", ""


def is_trusted_news_source(source_name: str | None) -> bool:
    name = (source_name or "").strip().lower()
    return any(candidate.lower() == name for candidate in TRUSTED_NEWS_SOURCES)


def _default_get(url: str, params: dict[str, str], timeout: int = 30) -> dict[str, Any]:
    if not url.startswith(GNEWS_SEARCH_URL):
        raise RuntimeError("GNews intake may only call https://gnews.io/api/v4/search")
    request = Request(
        f"{url}?{urlencode(params)}",
        headers={"Accept": "application/json", "User-Agent": "ts-regulatory-monitor/0.1"},
    )
    with urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8", errors="replace"))


Transport = Callable[[str, dict[str, str]], dict[str, Any]]


def fetch_gnews(transport: Transport | None = None) -> list[dict[str, Any]]:
    """Fetch trusted English articles. Failures are skipped so official intake can continue."""
    _name, key = resolve_gnews_key()
    if not key:
        return []
    get = transport or _default_get
    articles: list[dict[str, Any]] = []
    for query in GNEWS_KEYWORD_SETS:
        try:
            payload = get(
                GNEWS_SEARCH_URL,
                {"q": query, "lang": "en", "max": "10", "apikey": key},
            )
        except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError, RuntimeError):
            continue
        except Exception:
            continue
        for article in payload.get("articles") or []:
            source = article.get("source") or {}
            source_name = source.get("name") or ""
            if not is_trusted_news_source(source_name):
                continue
            title = str(article.get("title") or "").strip()
            url = str(article.get("url") or "").strip()
            if not title or not url:
                continue
            description = str(article.get("description") or article.get("content") or "").strip()
            articles.append(
                {
                    "title": title,
                    "url": url,
                    "description": description,
                    "content": description,
                    "publishedAt": str(article.get("publishedAt") or ""),
                    "source": {"name": source_name, "kind": "gnews"},
                    "monitoring_origin": "gnews",
                }
            )
    return articles
