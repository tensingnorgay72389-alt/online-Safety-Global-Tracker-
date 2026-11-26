"""Polite HTTP fetchers for RSS, HTML indexes and official pages."""

from __future__ import annotations

import os
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from ts_monitor.models import FetchError, InboxItem
from ts_monitor.parsers import extract_index_links, inbox_item_from_dict, parse_official_bill_html, slug_id
from ts_monitor.sources import Source, SourceCatalog, load_catalog
from ts_monitor.timeutil import iso, now_pair, pair_from, parse_datetime

HttpOpener = Callable[[str, str, int], tuple[int, str, str]]


def _default_open(url: str, user_agent: str, timeout: int) -> tuple[int, str, str]:
    request = Request(url, headers={"User-Agent": user_agent, "Accept": "text/html,application/rss+xml,application/atom+xml,application/xml,text/xml,*/*"})
    with urlopen(request, timeout=timeout) as response:
        status = int(getattr(response, "status", 200) or 200)
        charset = response.headers.get_content_charset() or "utf-8"
        body = response.read().decode(charset, errors="replace")
        final_url = str(response.geturl() or url)
        return status, body, final_url


class Fetcher:
    def __init__(
        self,
        catalog: SourceCatalog | None = None,
        opener: HttpOpener | None = None,
        user_agent: str | None = None,
        timeout: int | None = None,
    ):
        self.catalog = catalog or load_catalog()
        self.opener = opener or _default_open
        settings = self.catalog.fetch
        self.user_agent = user_agent or os.environ.get("TS_MONITOR_USER_AGENT") or settings.user_agent
        env_timeout = os.environ.get("TS_MONITOR_HTTP_TIMEOUT")
        self.timeout = int(timeout or env_timeout or settings.timeout_seconds)
        self.errors: list[FetchError] = []

    def _record_error(self, source: Source, url: str, error_type: str, message: str, status_code: int | None = None) -> None:
        hk, utc = now_pair()
        self.errors.append(
            FetchError(
                source_id=source.id,
                url=url,
                error_type=error_type,
                message=message,
                fetched_at=hk,
                fetched_at_utc=utc,
                status_code=status_code,
            )
        )

    def get(self, source: Source, url: str | None = None) -> tuple[str | None, str | None]:
        target = url or source.url
        try:
            status, body, final_url = self.opener(target, self.user_agent, self.timeout)
        except HTTPError as exc:
            error_type = f"http_{exc.code}"
            if exc.code == 403:
                error_type = "http_403"
            self._record_error(source, target, error_type, str(exc), status_code=exc.code)
            return None, None
        except URLError as exc:
            reason = str(getattr(exc, "reason", exc))
            error_type = "timeout" if "timed out" in reason.lower() or "timeout" in reason.lower() else "connection"
            self._record_error(source, target, error_type, reason)
            return None, None
        except TimeoutError as exc:
            self._record_error(source, target, "timeout", str(exc))
            return None, None
        except Exception as exc:  # pragma: no cover - defensive
            name = type(exc).__name__.lower()
            error_type = "timeout" if "timeout" in name else "error"
            self._record_error(source, target, error_type, str(exc))
            return None, None
        if status == 403:
            self._record_error(source, target, "http_403", "HTTP 403", status_code=403)
            return None, None
        if status >= 400:
            self._record_error(source, target, f"http_{status}", f"HTTP {status}", status_code=status)
            return None, None
        return body, target if not final_url else final_url

    def fetch_source(self, source: Source, since: str | None = None) -> list[InboxItem]:
        if source.method == "rss":
            return self._fetch_rss(source, since)
        if source.method == "official_page":
            return self._fetch_official_page(source)
        return self._fetch_html_index(source, since)

    def fetch_all(self, since: str | None = None, official_only: bool = False) -> list[InboxItem]:
        items: list[InboxItem] = []
        for source in self.catalog.sources:
            if official_only and not source.official:
                continue
            items.extend(self.fetch_source(source, since=since))
        return items

    def _after_since(self, published: str | None, since: str | None) -> bool:
        if not since or not published:
            return True
        parsed = parse_datetime(published)
        since_dt = parse_datetime(since)
        if parsed is None or since_dt is None:
            return True
        return parsed >= since_dt

    def _fetch_rss(self, source: Source, since: str | None) -> list[InboxItem]:
        body, _ = self.get(source)
        if body is None:
            return []
        try:
            root = ET.fromstring(body)
        except ET.ParseError as exc:
            self._record_error(source, source.url, "parse_error", str(exc))
            return []
        items: list[InboxItem] = []
        # RSS 2.0 and Atom.
        entries = list(root.findall("./channel/item")) + list(root.findall(".//{http://www.w3.org/2005/Atom}entry"))
        if not entries:
            entries = list(root.findall(".//item"))
        for entry in entries:
            title = _child_text(entry, "title") or ""
            link = _child_text(entry, "link") or _atom_link(entry)
            published = _child_text(entry, "pubDate") or _child_text(entry, "published") or _child_text(entry, "updated")
            published_iso = _rss_date(published)
            if not self._after_since(published_iso, since):
                continue
            summary = _child_text(entry, "description") or _child_text(entry, "summary")
            items.append(
                inbox_item_from_dict(
                    {
                        "id": slug_id(f"{source.id}-{title or link}"),
                        "headline": title,
                        "outlet": source.name,
                        "published_date": published_iso[:10] if published_iso else None,
                        "url": link,
                        "summary": summary,
                        "source_id": source.id,
                        "source_kind": source.role,
                        "jurisdiction_hint": source.jurisdiction,
                    }
                )
            )
        return items

    def _fetch_html_index(self, source: Source, since: str | None) -> list[InboxItem]:
        body, final_url = self.get(source)
        if body is None:
            return []
        links = extract_index_links(body, final_url or source.url, limit=self.catalog.fetch.max_index_links)
        fetched_at, fetched_at_utc = now_pair()
        items: list[InboxItem] = []
        for link in links:
            items.append(
                inbox_item_from_dict(
                    {
                        "id": slug_id(f"{source.id}-{link}"),
                        "headline": link,
                        "outlet": source.name,
                        "url": link,
                        "source_id": source.id,
                        "source_kind": source.role,
                        "jurisdiction_hint": source.jurisdiction,
                        "fetched_at": fetched_at,
                        "fetched_at_utc": fetched_at_utc,
                    }
                )
            )
        return items

    def _fetch_official_page(self, source: Source) -> list[InboxItem]:
        body, final_url = self.get(source)
        if body is None:
            return []
        parsed = parse_official_bill_html(body)
        fetched_at, fetched_at_utc = now_pair()
        headline = source.name
        if parsed.get("raw_status_text"):
            headline = f"{source.name} — official status {parsed['raw_status_text']}"
        return [
            inbox_item_from_dict(
                {
                    "id": slug_id(f"{source.id}-official-page"),
                    "headline": headline,
                    "outlet": source.name,
                    "url": final_url or source.url,
                    "official_document_url": final_url or source.url,
                    "summary": (parsed.get("text") or "")[:1500],
                    "source_id": source.id,
                    "source_kind": source.role,
                    "jurisdiction_hint": source.jurisdiction,
                    "raw_status_text": parsed.get("raw_status_text"),
                    "raw_assent_listed": parsed.get("raw_assent_listed"),
                    "fetched_at": fetched_at,
                    "fetched_at_utc": fetched_at_utc,
                }
            )
        ]


def _child_text(element: ET.Element, name: str) -> str | None:
    for child in list(element):
        tag = child.tag.split("}")[-1]
        if tag == name:
            if child.text and child.text.strip():
                return child.text.strip()
            # Atom link text may be empty.
    return None


def _atom_link(element: ET.Element) -> str | None:
    for child in list(element):
        tag = child.tag.split("}")[-1]
        if tag == "link":
            href = child.attrib.get("href")
            if href:
                return href
            if child.text and child.text.strip().startswith("http"):
                return child.text.strip()
    return None


def _rss_date(value: str | None) -> str | None:
    if not value:
        return None
    try:
        parsed = parsedate_to_datetime(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return iso(parsed)
    except (TypeError, ValueError, OverflowError):
        parsed = parse_datetime(value)
        return iso(parsed) if parsed else value
