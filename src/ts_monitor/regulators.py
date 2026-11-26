"""Load the versioned regulator and ministry map and turn scrape targets into catalogue sources."""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import yaml

from ts_monitor.paths import default_regulators_path
from ts_monitor.sources import Source, SourceCatalog

ALLOWED_BODY_TYPES = {"regulator", "ministry", "parliament", "executive", "gazette", "commission"}
ALLOWED_HANDLE_STATUSES = {
    "listed_on_official_page",
    "not_listed_on_official_page",
    "not_retrieved",
    "unverified",
    "no_account_found",
}


@dataclass(frozen=True)
class Spokesperson:
    name: str
    role: str
    source_url: str
    official_profile_url: str | None = None
    source_retrieved_at: str | None = None
    appointed: str | None = None
    x_handle: str | None = None
    x_handle_url: str | None = None
    x_handle_status: str = "not_listed_on_official_page"
    notes: str | None = None


@dataclass(frozen=True)
class ScrapeTarget:
    id: str
    url: str
    method: str
    role: str
    auto_apply_eligible: bool
    official: bool = True
    name: str | None = None


@dataclass
class RegulatoryBody:
    id: str
    jurisdiction: str
    jurisdiction_name: str
    body_type: str
    official_name: str
    official_homepage: str | None
    scrape_targets: list[ScrapeTarget] = field(default_factory=list)
    newsroom_url: str | None = None
    media_release_url: str | None = None
    bill_or_consultation_url: str | None = None
    leadership_url: str | None = None
    official_x_handle: str | None = None
    official_x_handle_url: str | None = None
    official_x_handle_source_url: str | None = None
    spokespersons: list[Spokesperson] = field(default_factory=list)
    spokesperson_status: str | None = None
    evidence: list[str] = field(default_factory=list)
    retrieval_notes: list[str] = field(default_factory=list)
    notes: str | None = None


@dataclass
class RegulatorMap:
    version: str
    as_of: str
    notes: str | None
    bodies: list[RegulatoryBody]

    def by_id(self, body_id: str) -> RegulatoryBody | None:
        for body in self.bodies:
            if body.id == body_id:
                return body
        return None

    def counts(self) -> dict[str, int]:
        people = sum(len(body.spokespersons) for body in self.bodies)
        handles = sum(
            1
            for body in self.bodies
            for person in body.spokespersons
            if person.x_handle
        )
        institutional = sum(1 for body in self.bodies if body.official_x_handle)
        targets = sum(len(body.scrape_targets) for body in self.bodies)
        return {
            "bodies": len(self.bodies),
            "spokespersons": people,
            "personal_handles": handles,
            "institutional_handles": institutional,
            "scrape_targets": targets,
        }


def _person(raw: dict[str, Any]) -> Spokesperson:
    handle = raw.get("x_handle")
    handle = str(handle) if handle else None
    status = str(raw.get("x_handle_status") or ("listed_on_official_page" if handle else "not_listed_on_official_page"))
    if status not in ALLOWED_HANDLE_STATUSES:
        status = "unverified"
    if handle and status != "listed_on_official_page":
        # A handle may only be stored when an official page (or loaded profile) identified it.
        handle = None
    return Spokesperson(
        name=str(raw["name"]),
        role=str(raw["role"]),
        source_url=str(raw["source_url"]),
        official_profile_url=raw.get("official_profile_url"),
        source_retrieved_at=raw.get("source_retrieved_at"),
        appointed=raw.get("appointed"),
        x_handle=handle,
        x_handle_url=raw.get("x_handle_url") if handle else None,
        x_handle_status=status if handle else (status if status != "listed_on_official_page" else "not_listed_on_official_page"),
        notes=raw.get("notes"),
    )


def _target(raw: dict[str, Any], body: dict[str, Any], index: int) -> ScrapeTarget:
    url = str(raw["url"])
    return ScrapeTarget(
        id=str(raw.get("id") or f"{body['id']}-target-{index}"),
        url=url,
        method=str(raw.get("method") or "html_index"),
        role=str(raw.get("role") or "regulator_newsroom"),
        auto_apply_eligible=bool(raw.get("auto_apply_eligible", True)),
        official=bool(raw.get("official", True)),
        name=raw.get("name") or raw.get("label"),
    )


def _body(raw: dict[str, Any]) -> RegulatoryBody:
    body_type = str(raw["body_type"])
    if body_type not in ALLOWED_BODY_TYPES:
        raise ValueError(f"Unsupported body_type {body_type!r} on {raw.get('id')}")
    targets_raw = list(raw.get("scrape_targets") or [])
    # If no explicit targets, derive them from the standard URL fields.
    if not targets_raw:
        derived = []
        if raw.get("newsroom_url"):
            derived.append({"url": raw["newsroom_url"], "method": raw.get("fetch_method") or "newsroom", "role": "regulator_newsroom"})
        if raw.get("media_release_url"):
            derived.append({"url": raw["media_release_url"], "method": "newsroom", "role": "ministerial_release" if raw["body_type"] == "ministry" else "regulator_newsroom", "auto_apply_eligible": raw["body_type"] != "ministry"})
        if raw.get("bill_or_consultation_url"):
            derived.append({"url": raw["bill_or_consultation_url"], "method": "html_index", "role": "instrument"})
        targets_raw = derived
    return RegulatoryBody(
        id=str(raw["id"]),
        jurisdiction=str(raw["jurisdiction"]),
        jurisdiction_name=str(raw.get("jurisdiction_name") or raw["jurisdiction"]),
        body_type=body_type,
        official_name=str(raw["official_name"]),
        official_homepage=raw.get("official_homepage"),
        scrape_targets=[_target(item, raw, i) for i, item in enumerate(targets_raw, 1)],
        newsroom_url=raw.get("newsroom_url"),
        media_release_url=raw.get("media_release_url"),
        bill_or_consultation_url=raw.get("bill_or_consultation_url"),
        leadership_url=raw.get("leadership_url"),
        official_x_handle=raw.get("official_x_handle"),
        official_x_handle_url=raw.get("official_x_handle_url"),
        official_x_handle_source_url=raw.get("official_x_handle_source_url"),
        spokespersons=[_person(item) for item in raw.get("spokespersons") or []],
        spokesperson_status=raw.get("spokesperson_status"),
        evidence=list(raw.get("evidence") or []),
        retrieval_notes=list(raw.get("retrieval_notes") or []),
        notes=raw.get("notes"),
    )


@lru_cache(maxsize=4)
def load_regulator_map(path: str | Path | None = None) -> RegulatorMap:
    location = Path(path) if path else default_regulators_path()
    raw = yaml.safe_load(location.read_text(encoding="utf-8"))
    bodies = [_body(item) for item in raw.get("bodies") or []]
    return RegulatorMap(
        version=str(raw.get("version") or "0"),
        as_of=str(raw.get("as_of") or ""),
        notes=raw.get("notes"),
        bodies=bodies,
    )


def sources_from_regulators(reg_map: RegulatorMap) -> list[Source]:
    sources: list[Source] = []
    for body in reg_map.bodies:
        for target in body.scrape_targets:
            role = target.role
            auto = target.auto_apply_eligible
            if role == "ministerial_release":
                auto = False
            sources.append(
                Source(
                    id=target.id,
                    name=target.name or f"{body.official_name} ({target.role})",
                    url=target.url,
                    method=target.method,
                    official=target.official,
                    auto_apply_eligible=auto,
                    role=role,
                    jurisdiction=body.jurisdiction,
                    notes=f"Regulator map body {body.id}",
                )
            )
    return sources


def merge_source_catalog(catalog: SourceCatalog, extras: list[Source]) -> SourceCatalog:
    def key(url: str) -> str:
        parsed = urlparse(url)
        host = (parsed.netloc or "").lower().removeprefix("www.")
        path = (parsed.path or "/").rstrip("/") or "/"
        return f"{host}{path}"

    seen = {key(source.url) for source in catalog.sources if source.url}
    merged = list(catalog.sources)
    for source in extras:
        token = key(source.url)
        if token in seen:
            continue
        merged.append(source)
        seen.add(token)
    return SourceCatalog(sources=merged, fetch=catalog.fetch)
