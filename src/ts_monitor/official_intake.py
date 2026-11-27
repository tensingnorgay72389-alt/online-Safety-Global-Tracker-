"""Collect candidate items from the expanded official-source inventory.

There is no cap of 20 and the original curated list is not the limit.
RSS or Atom is preferred. Otherwise a feed link is discovered, then a few
candidate article links are scraped. HTTP 403 is recorded and the source stays
in the inventory. A block is not treated as proof that the source is dead.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

from ts_monitor.official_inventory import OfficialInventory, row_is_pollable

CANDIDATE_LINKS_PER_SOURCE = 4
DISCOVERY_KEYWORDS = (
    "age",
    "child",
    "children",
    "minor",
    "youth",
    "safety",
    "online",
    "platform",
    "social",
    "digital",
    "verification",
    "assurance",
    "regulat",
    "law",
    "bill",
    "act",
    "enforcement",
    "guidance",
    "consult",
    "media",
    "news",
    "press",
    "csam",
    "deepfake",
    "chatbot",
    "gaming",
    "companion",
    "intimate",
)
ARTICLE_PATH_HINTS = (
    "/news/",
    "/press/",
    "/media/",
    "/announcement",
    "/consult",
    "/guidance",
    "/bill",
    "/legislation",
)
IGNORED_SUFFIXES = (".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp", ".zip", ".css", ".js", ".pdf")


@dataclass
class PageFetch:
    url: str
    status: int | None
    body: str = ""
    content_type: str = ""
    final_url: str = ""
    error: str | None = None

    @property
    def blocked(self) -> bool:
        return self.status == 403 or (self.error or "").startswith("http_403")


def sources_to_collect(inventory: OfficialInventory) -> list[dict[str, Any]]:
    """Every pollable inventory row, including unverified-blocked URLs."""
    return [row for row in inventory.rows if row_is_pollable(row)]


def _default_fetch(url: str, timeout: int | None = None) -> PageFetch:
    limit = timeout or int(os.environ.get("TS_MONITOR_HTTP_TIMEOUT") or 12)
    request = Request(
        url,
        headers={
            "User-Agent": os.environ.get("TS_MONITOR_USER_AGENT")
            or "ts-regulatory-monitor/0.1 (research monitoring; polite fetch)",
            "Accept": "text/html,application/rss+xml,application/atom+xml,application/xml,text/xml,*/*",
        },
    )
    try:
        with urlopen(request, timeout=limit) as response:
            status = int(getattr(response, "status", 200) or 200)
            charset = response.headers.get_content_charset() or "utf-8"
            body = response.read().decode(charset, errors="replace")
            content_type = response.headers.get("Content-Type") or ""
            final_url = str(response.geturl() or url)
            return PageFetch(url=url, status=status, body=body, content_type=content_type, final_url=final_url)
    except HTTPError as exc:
        return PageFetch(url=url, status=int(exc.code), error=f"http_{exc.code}")
    except (URLError, TimeoutError, OSError) as exc:
        reason = str(getattr(exc, "reason", exc))
        kind = "timeout" if "timed out" in reason.lower() else "connection"
        return PageFetch(url=url, status=None, error=kind)


class _LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.feed_links: list[str] = []
        self.anchors: list[tuple[str, str]] = []
        self._href = ""
        self._text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        data = {key.lower(): (value or "") for key, value in attrs}
        if tag == "link":
            rel = data.get("rel", "").lower()
            href = data.get("href", "")
            kind = data.get("type", "").lower()
            if href and "alternate" in rel and ("rss" in kind or "atom" in kind or href.endswith(".xml")):
                self.feed_links.append(href)
        if tag == "a":
            self._href = data.get("href", "")
            self._text = []

    def handle_data(self, data: str) -> None:
        if self._href:
            self._text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._href:
            self.anchors.append((self._href, " ".join(self._text)))
            self._href = ""
            self._text = []


def looks_like_feed(url: str, content_type: str, body: str) -> bool:
    content_type = (content_type or "").lower()
    sample = body.lstrip()[:500].lower()
    return (
        "xml" in content_type
        or url.lower().endswith((".xml", ".rss", ".atom"))
        or sample.startswith("<?xml")
        or "<rss" in sample
        or "<feed" in sample
    )


def prefers_feed(row: dict[str, Any]) -> bool:
    adapter = str(row.get("adapter") or "").lower()
    kind = str(row.get("endpoint_kind") or "").lower()
    url = str(row.get("url") or "").lower()
    return adapter == "rss" or kind == "rss" or url.endswith((".xml", ".rss", ".atom"))


def _child_text(node: ET.Element, name: str) -> str:
    for child in list(node):
        if child.tag == name or child.tag.endswith("}" + name):
            return "".join(child.itertext()).strip()
    return ""


def parse_feed_items(xml_text: str, source_name: str, source_url: str) -> list[dict[str, Any]]:
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []
    entries = list(root.findall("./channel/item")) + list(root.findall(".//{http://www.w3.org/2005/Atom}entry"))
    if not entries:
        entries = list(root.findall(".//item"))
    articles: list[dict[str, Any]] = []
    for entry in entries:
        title = _child_text(entry, "title")
        link = _child_text(entry, "link")
        if not link:
            for child in list(entry):
                if child.tag.endswith("}link") and child.attrib.get("href"):
                    link = child.attrib["href"]
                    break
        if not title or not link:
            continue
        description = _child_text(entry, "description") or _child_text(entry, "summary")
        published = _child_text(entry, "pubDate") or _child_text(entry, "published") or _child_text(entry, "updated")
        articles.append(
            {
                "title": title,
                "url": link,
                "description": description,
                "content": description,
                "publishedAt": published,
                "source": {"name": source_name, "kind": "official_feed"},
                "monitoring_origin": "official_feed",
                "inventory_url": source_url,
            }
        )
    return articles


def _candidate_urls(page_url: str, parser: _LinkParser) -> list[str]:
    host = urlparse(page_url).netloc.lower().removeprefix("www.")
    scored: list[tuple[int, str]] = []
    seen: set[str] = set()
    for href, text in parser.anchors:
        absolute = urljoin(page_url, href)
        parsed = urlparse(absolute)
        if parsed.scheme not in {"http", "https"}:
            continue
        if absolute.lower().endswith(IGNORED_SUFFIXES):
            continue
        link_host = parsed.netloc.lower().removeprefix("www.")
        if host and link_host and link_host != host:
            continue
        blob = f"{text} {absolute}".lower()
        score = sum(1 for keyword in DISCOVERY_KEYWORDS if keyword in blob)
        score += sum(2 for hint in ARTICLE_PATH_HINTS if hint in absolute.lower())
        if score <= 0:
            continue
        token = absolute.rstrip("/")
        if token in seen:
            continue
        seen.add(token)
        scored.append((score, absolute))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [url for _score, url in scored[:CANDIDATE_LINKS_PER_SOURCE]]


def collect_official(
    rows: list[dict[str, Any]],
    fetch: Callable[[str], PageFetch] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Fetch every supplied row. Blocked URLs are attempted and then recorded."""
    getter = fetch or _default_fetch
    articles: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    for row in rows:
        source_url = str(row.get("url") or "").strip()
        source_name = str(row.get("source_name") or row.get("source_id") or source_url)
        if not source_url:
            continue
        page = getter(source_url)
        if page.blocked or page.error or (page.status is not None and page.status >= 400):
            errors.append(
                {
                    "source_id": row.get("source_id"),
                    "url": source_url,
                    "status": page.status,
                    "error": page.error or f"http_{page.status}",
                    "verification_status": row.get("verification_status") or "",
                    "dead": False,
                }
            )
            continue
        feed_body = looks_like_feed(page.final_url or page.url, page.content_type, page.body)
        if feed_body or prefers_feed(row):
            parsed = parse_feed_items(page.body, source_name, source_url) if page.body else []
            if parsed:
                articles.extend(parsed)
                continue
            errors.append(
                {
                    "source_id": row.get("source_id"),
                    "url": source_url,
                    "status": page.status,
                    "error": "feed_not_parsed",
                    "verification_status": row.get("verification_status") or "",
                    "dead": False,
                }
            )
            if prefers_feed(row):
                continue
        parser = _LinkParser()
        parser.feed(page.body or "")
        loaded_feed = False
        for href in parser.feed_links[:1]:
            feed_url = urljoin(page.final_url or source_url, href)
            feed_page = getter(feed_url)
            parsed = parse_feed_items(feed_page.body, source_name, source_url) if feed_page.body else []
            if parsed:
                articles.extend(parsed)
                loaded_feed = True
                break
        if loaded_feed:
            continue
        for candidate in _candidate_urls(page.final_url or source_url, parser):
            candidate_page = getter(candidate)
            if candidate_page.blocked or candidate_page.error or not candidate_page.body:
                errors.append(
                    {
                        "source_id": row.get("source_id"),
                        "url": candidate,
                        "status": candidate_page.status,
                        "error": candidate_page.error or "empty",
                        "verification_status": row.get("verification_status") or "",
                        "dead": False,
                    }
                )
                continue
            title = source_name
            if "<title>" in candidate_page.body.lower():
                start = candidate_page.body.lower().find("<title>")
                end = candidate_page.body.lower().find("</title>", start)
                if start >= 0 and end > start:
                    title = candidate_page.body[start + 7 : end].strip() or title
            description = title
            articles.append(
                {
                    "title": " ".join(title.split()),
                    "url": candidate_page.final_url or candidate,
                    "description": description,
                    "content": description,
                    "publishedAt": "",
                    "source": {"name": source_name, "kind": "official_page"},
                    "monitoring_origin": "official_page",
                    "inventory_url": source_url,
                }
            )
    return articles, errors
