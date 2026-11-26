"""Typed records for inbox items, register instruments and proposal patches."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from typing import Any, Literal

ProposalAction = Literal["new_instrument", "status_change", "milestone_add", "news_only"]
Confidence = Literal["high", "medium", "low"]


def _clean(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return {k: _clean(v) for k, v in asdict(value).items()}
    if isinstance(value, dict):
        return {k: _clean(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_clean(v) for v in value]
    return value


@dataclass(frozen=True)
class SourceRef:
    url: str
    kind: str
    title: str | None = None
    source_id: str | None = None


@dataclass
class InboxItem:
    id: str
    headline: str
    outlet: str | None = None
    published_date: str | None = None
    url: str | None = None
    summary: str | None = None
    body: str | None = None
    section: str | None = None
    source_id: str | None = None
    source_kind: str | None = None
    jurisdiction_hint: str | None = None
    official_document_url: str | None = None
    raw_status_text: str | None = None
    raw_assent_listed: bool | None = None
    fetched_at: str | None = None
    fetched_at_utc: str | None = None
    proposed_fields: dict[str, Any] = field(default_factory=dict)
    extra: dict[str, Any] = field(default_factory=dict)

    def text(self) -> str:
        parts = [
            self.headline or "",
            self.outlet or "",
            self.summary or "",
            self.body or "",
            self.section or "",
            self.raw_status_text or "",
            self.url or "",
            self.official_document_url or "",
        ]
        return "\n".join(parts)

    def primary_url(self) -> str | None:
        return self.official_document_url or self.url

    def to_dict(self) -> dict[str, Any]:
        return _clean(self)


@dataclass(frozen=True)
class Milestone:
    regulation_id: str
    type: str
    date: str | None
    description: str | None
    source_url: str | None = None


@dataclass
class RegisterInstrument:
    id: str
    name: str
    official_title: str | None
    jurisdiction_id: str
    jurisdiction_name: str | None
    year: int | None
    status: str
    instrument_kind: str | None
    service_type_ids: list[str]
    source_url: str | None
    effective_date: str | None
    summary: str | None
    milestones: list[Milestone] = field(default_factory=list)
    aliases: list[str] = field(default_factory=list)

    def to_compact(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "official_title": self.official_title,
            "jid": self.jurisdiction_id,
            "jname": self.jurisdiction_name,
            "year": self.year,
            "status": self.status,
            "kind": self.instrument_kind,
            "services": list(self.service_type_ids),
            "source": self.source_url,
            "effective": self.effective_date,
            "summary": self.summary,
        }


@dataclass
class MatchResult:
    instrument: RegisterInstrument | None
    score: float = 0.0
    reason: str | None = None


@dataclass
class EpistemicMark:
    sourced_facts: list[dict[str, Any]] = field(default_factory=list)
    category_judgement: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "sourced_facts": list(self.sourced_facts),
            "category_judgement": list(self.category_judgement),
        }


@dataclass
class Proposal:
    proposal_id: str
    action: ProposalAction
    instrument_id: str | None
    proposed_id: str | None
    fields: dict[str, Any]
    previous_values: dict[str, Any] | None
    significant: bool
    confidence: Confidence
    sources: list[SourceRef]
    fetched_at: str
    fetched_at_utc: str
    notes: str
    epistemic: EpistemicMark
    inbox_item_id: str
    vocabulary_flags: list[str] = field(default_factory=list)
    auto_apply_eligible: bool = False
    rejected: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "proposal_id": self.proposal_id,
            "action": self.action,
            "instrument_id": self.instrument_id,
            "proposed_id": self.proposed_id,
            "fields": self.fields,
            "previous_values": self.previous_values,
            "significant": self.significant,
            "confidence": self.confidence,
            "sources": [_clean(s) for s in self.sources],
            "fetched_at": self.fetched_at,
            "fetched_at_utc": self.fetched_at_utc,
            "notes": self.notes,
            "epistemic": self.epistemic.to_dict(),
            "inbox_item_id": self.inbox_item_id,
            "vocabulary_flags": list(self.vocabulary_flags),
            "auto_apply_eligible": self.auto_apply_eligible,
            "rejected": self.rejected,
        }


@dataclass
class FetchError:
    source_id: str
    url: str
    error_type: str
    message: str
    fetched_at: str
    fetched_at_utc: str
    status_code: int | None = None
    note: str = (
        "This failure was not treated as evidence that the page does not exist."
    )

    def to_dict(self) -> dict[str, Any]:
        return _clean(self)
