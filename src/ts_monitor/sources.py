"""Load the curated source catalogue and classify URLs."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import yaml

from ts_monitor.paths import default_sources_path


@dataclass(frozen=True)
class Source:
    id: str
    name: str
    url: str
    method: str
    official: bool
    auto_apply_eligible: bool
    role: str
    jurisdiction: str | None = None
    notes: str | None = None


@dataclass(frozen=True)
class FetchSettings:
    timeout_seconds: int = 20
    user_agent: str = "ts-regulatory-monitor/0.1 (research monitoring; polite fetch)"
    max_index_links: int = 40


@dataclass
class SourceCatalog:
    sources: list[Source]
    fetch: FetchSettings

    def by_id(self, source_id: str | None) -> Source | None:
        if not source_id:
            return None
        for source in self.sources:
            if source.id == source_id:
                return source
        return None

    def matching_url(self, url: str | None) -> Source | None:
        if not url:
            return None
        parsed = urlparse(url)
        host = (parsed.netloc or "").lower().removeprefix("www.")
        # Prefer the longest matching official or exact URL.
        exact: list[Source] = []
        host_hits: list[Source] = []
        for source in self.sources:
            source_url = source.url or ""
            if url.rstrip("/") == source_url.rstrip("/"):
                exact.append(source)
                continue
            source_host = urlparse(source_url).netloc.lower().removeprefix("www.")
            if host and source_host and (host == source_host or host.endswith("." + source_host) or source_host.endswith("." + host)):
                host_hits.append(source)
            elif source_url and source_url.rstrip("/") in url:
                host_hits.append(source)
        if exact:
            exact.sort(key=lambda s: (s.official, s.auto_apply_eligible, len(s.url)), reverse=True)
            return exact[0]
        if host_hits:
            host_hits.sort(key=lambda s: (s.official, s.auto_apply_eligible, len(s.url)), reverse=True)
            return host_hits[0]
        return None

    def official_urls(self) -> list[str]:
        return [s.url for s in self.sources if s.official]


@lru_cache(maxsize=4)
def load_catalog(path: str | Path | None = None) -> SourceCatalog:
    location = Path(path) if path else default_sources_path()
    raw = yaml.safe_load(location.read_text(encoding="utf-8"))
    fetch_raw = raw.get("fetch") or {}
    fetch = FetchSettings(
        timeout_seconds=int(fetch_raw.get("timeout_seconds") or 20),
        user_agent=str(fetch_raw.get("user_agent") or FetchSettings.user_agent),
        max_index_links=int(fetch_raw.get("max_index_links") or 40),
    )
    sources: list[Source] = []
    for entry in raw.get("sources") or []:
        sources.append(
            Source(
                id=str(entry["id"]),
                name=str(entry["name"]),
                url=str(entry["url"]),
                method=str(entry.get("method") or "html_index"),
                official=bool(entry.get("official")),
                auto_apply_eligible=bool(entry.get("auto_apply_eligible")),
                role=str(entry.get("role") or ("instrument" if entry.get("official") else "news")),
                jurisdiction=entry.get("jurisdiction"),
                notes=entry.get("notes"),
            )
        )
    return SourceCatalog(sources=sources, fetch=fetch)


def source_kind_for(url: str | None, catalog: SourceCatalog, explicit: str | None = None) -> str:
    if explicit:
        return explicit
    source = catalog.matching_url(url)
    if not source:
        return "news"
    return source.role


def is_official_url(url: str | None, catalog: SourceCatalog) -> bool:
    source = catalog.matching_url(url)
    return bool(source and source.official)


def host_of(url: str | None) -> str:
    if not url:
        return ""
    return urlparse(url).netloc.lower().removeprefix("www.")
