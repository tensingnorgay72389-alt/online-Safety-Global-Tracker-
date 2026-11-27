"""Deduplicate intake items by URL and by title similarity."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any


TITLE_SIMILARITY_THRESHOLD = 0.85


def normalise_url(url: str | None) -> str:
    return (url or "").strip().lower().rstrip("/")


def title_similarity(left: str, right: str) -> float:
    return SequenceMatcher(None, left.lower(), right.lower()).ratio()


def load_seen(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"version": "1.0.0", "last_updated": None, "total_count": 0, "urls": {}, "titles": []}
    data = json.loads(path.read_text(encoding="utf-8"))
    data.setdefault("urls", {})
    data.setdefault("titles", [])
    return data


def deduplicate(articles: list[dict[str, Any]], seen: dict[str, Any]) -> list[dict[str, Any]]:
    """Drop URLs already seen and titles that are near-duplicates of a seen or batch title."""
    seen_urls = {normalise_url(url) for url in (seen.get("urls") or {})}
    seen_titles = [str(title) for title in (seen.get("titles") or []) if str(title).strip()]
    unique: list[dict[str, Any]] = []
    for article in articles:
        url = normalise_url(str(article.get("url") or ""))
        title = str(article.get("title") or "").strip()
        if not url or not title:
            continue
        if url in seen_urls:
            continue
        if any(title_similarity(title, previous) > TITLE_SIMILARITY_THRESHOLD for previous in seen_titles):
            continue
        seen_urls.add(url)
        seen_titles.append(title)
        unique.append(article)
    return unique


def remember(seen: dict[str, Any], articles: list[dict[str, Any]]) -> dict[str, Any]:
    urls = dict(seen.get("urls") or {})
    titles = [str(title) for title in (seen.get("titles") or [])]
    now = datetime.now(timezone.utc).isoformat()
    for article in articles:
        url = normalise_url(str(article.get("url") or ""))
        title = str(article.get("title") or "").strip()
        if url and url not in urls:
            urls[url] = {"url": article.get("url"), "first_seen": now}
        if title and title not in titles:
            titles.append(title)
    return {
        "version": "1.0.0",
        "last_updated": now,
        "total_count": len(urls),
        "urls": urls,
        "titles": titles,
    }


def save_seen(path: Path, seen: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(seen, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
