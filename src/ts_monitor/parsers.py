"""Normalise Word-report-like JSON and parse official instrument pages."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from ts_monitor.models import InboxItem
from ts_monitor.timeutil import pair_from

_PASSED_BOTH = re.compile(r"passed both houses", re.I)
_ASSENT_LISTED = re.compile(
    r"royal assent(?:\s*(?:on|:))?\s*(\d{1,2}\s+\w+\s+\d{4}|\d{4}-\d{2}-\d{2})",
    re.I,
)
_ASSENT_NOT_LISTED = re.compile(
    r"royal assent.{0,40}(not listed|not yet|awaiting|has not|no royal assent)|"
    r"(not|no).{0,20}royal assent",
    re.I,
)


def slug_id(value: str, prefix: str = "item") -> str:
    text = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    text = text[:60] or "item"
    return f"{prefix}-{text}"


def parse_official_bill_html(html: str) -> dict[str, Any]:
    """Extract a status field and whether Royal Assent is listed from official bill HTML."""
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True)
    status_text = None
    # Prefer an explicit Status field when present.
    match = re.search(r"status\s*[:\-]\s*([A-Za-z][A-Za-z ]{2,40})", text, re.I)
    if match:
        status_text = match.group(1).strip()
    elif _PASSED_BOTH.search(text):
        status_text = "Passed Both Houses"
    assent_listed = False
    assent_date = None
    if _ASSENT_NOT_LISTED.search(text) and not _ASSENT_LISTED.search(text):
        assent_listed = False
    else:
        listed = _ASSENT_LISTED.search(text)
        if listed:
            assent_listed = True
            assent_date = listed.group(1)
    return {
        "raw_status_text": status_text,
        "raw_assent_listed": assent_listed,
        "assent_date": assent_date,
        "passed_both_houses": bool(_PASSED_BOTH.search(text) or (status_text and _PASSED_BOTH.search(status_text))),
        "text": text,
    }


def _as_item_dict(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise TypeError("Inbox items must be JSON objects")
    return raw


def _first(*values: Any) -> Any:
    for value in values:
        if value is not None and value != "":
            return value
    return None


def inbox_item_from_dict(raw: dict[str, Any], default_fetched_at: str | None = None) -> InboxItem:
    headline = str(_first(raw.get("headline"), raw.get("title"), raw.get("name")) or "")
    url = _first(raw.get("url"), raw.get("link"))
    official = _first(raw.get("official_document_url"), raw.get("official_url"))
    published = _first(raw.get("published_date"), raw.get("date"), raw.get("published"))
    if hasattr(published, "isoformat"):
        published = published.isoformat()[:10]
    elif published:
        published = str(published)[:10]
    fetched_at, fetched_at_utc = pair_from(_first(raw.get("fetched_at"), default_fetched_at))
    if raw.get("fetched_at_utc"):
        fetched_at_utc = str(raw["fetched_at_utc"])
    item_id = str(_first(raw.get("id"), slug_id(headline or url or "item")))
    return InboxItem(
        id=item_id,
        headline=headline,
        outlet=_first(raw.get("outlet"), raw.get("source_name"), raw.get("publisher")),
        published_date=published,
        url=url,
        summary=_first(raw.get("summary"), raw.get("description"), raw.get("text")),
        body=raw.get("body"),
        section=raw.get("section"),
        source_id=raw.get("source_id"),
        source_kind=raw.get("source_kind"),
        jurisdiction_hint=_first(raw.get("jurisdiction_hint"), raw.get("jurisdiction"), raw.get("jid")),
        official_document_url=official,
        raw_status_text=raw.get("raw_status_text"),
        raw_assent_listed=raw.get("raw_assent_listed"),
        fetched_at=fetched_at,
        fetched_at_utc=fetched_at_utc,
        proposed_fields=dict(raw.get("proposed_fields") or {}),
        extra={k: v for k, v in raw.items() if k not in {
            "id", "headline", "title", "name", "outlet", "source_name", "publisher",
            "published_date", "date", "published", "url", "link", "summary", "description",
            "text", "body", "section", "source_id", "source_kind", "jurisdiction_hint",
            "jurisdiction", "jid", "official_document_url", "official_url",
            "raw_status_text", "raw_assent_listed", "fetched_at", "fetched_at_utc",
            "proposed_fields",
        }},
    )


def load_items_file(path: str | Path) -> list[InboxItem]:
    """Load a Word-report-like JSON file, a list of items, or a single item object."""
    location = Path(path)
    if location.is_dir():
        items: list[InboxItem] = []
        for child in sorted(location.glob("*.json")):
            items.extend(load_items_file(child))
        return items
    raw = json.loads(location.read_text(encoding="utf-8"))
    return load_items_payload(raw)


def load_items_payload(raw: Any) -> list[InboxItem]:
    if isinstance(raw, list):
        rows = raw
    elif isinstance(raw, dict) and isinstance(raw.get("items"), list):
        rows = raw["items"]
    elif isinstance(raw, dict):
        rows = [raw]
    else:
        raise TypeError("Expected a JSON object, a list of items, or an object with an items array")
    return [inbox_item_from_dict(_as_item_dict(row)) for row in rows]


def extract_index_links(html: str, base_url: str, limit: int = 40) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    found: list[str] = []
    base = urlparse(base_url)
    for tag in soup.find_all("a", href=True):
        href = tag["href"].strip()
        if href.startswith("#") or href.lower().startswith("javascript:"):
            continue
        if href.startswith("//"):
            href = f"{base.scheme}:{href}"
        elif href.startswith("/"):
            href = f"{base.scheme}://{base.netloc}{href}"
        elif not href.startswith("http"):
            continue
        if href not in found:
            found.append(href)
        if len(found) >= limit:
            break
    return found
