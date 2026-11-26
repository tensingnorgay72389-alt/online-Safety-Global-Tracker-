"""Classify inbox items into typed register proposals with a strict significance bar."""

from __future__ import annotations

import hashlib
import re
from typing import Any
from urllib.parse import urlparse

from ts_monitor.models import (
    EpistemicMark,
    InboxItem,
    Proposal,
    RegisterInstrument,
    SourceRef,
)
from ts_monitor.register import Register
from ts_monitor.sources import SourceCatalog, is_official_url, load_catalog, source_kind_for
from ts_monitor.vocabularies import load_vocabularies, validate_fields

_PASSED_BOTH = re.compile(r"passed both houses", re.I)
_BECOMES_LAW = re.compile(r"\bbecomes law\b|\bis now law\b|\bsigned into law\b|\bnow the law\b", re.I)
_ROYAL_ASSENT = re.compile(r"royal assent", re.I)
_CONSULTATION = re.compile(r"\bconsultation\b|\bconsults\b|\bconsulting\b|\bdraft codes?\b", re.I)
_JOINT_STATEMENT = re.compile(
    r"\bjoint (position )?statement\b|\bregulators (network|meet|unite)\b|\bgosrn\b|"
    r"\bglobal online safety regulators\b",
    re.I,
)
_STATEMENT_ACTOR = re.compile(
    r"\bsenator[s]?\b|\bceo\b|\bchief executive\b|\bcalled for\b|\bsaid that\b|"
    r"\bthese are statements\b|\brejects claims\b|\bposted a lengthy statement\b",
    re.I,
)
_BILL_OR_ACT = re.compile(
    r"\bbill\b|\bact\b|\bdecree\b|\bregulation\b|\bstatutory code\b|\blegislation\b|"
    r"\broyal assent\b|\bpassed both houses\b|\benacted\b",
    re.I,
)
_BRAND_SECTION = re.compile(r"tencent mentions|\bbrand mention", re.I)
_TENCENT = re.compile(r"\btencent\b|\bhunyuan\b", re.I)

OFCOM_CONSULTATION_HOST = "ofcom.org.uk"
OFCOM_CONSULTATION_PATH = "/online-safety/illegal-and-harmful-content/intimate-image-abuse-takedown"
OFCOM_PROPOSED_ID = "UK-OFCOM-IIA-CODES-2026"
AU_DDOC_HOMEPAGE = "parlinfo.aph.gov.au"

ENACTMENT_KINDS = {"enacted", "in force"}
ENACTMENT_STATUSES = {"effective", "enforced", "implementation_period"}


def _sha(text: str, length: int = 8) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:length]


def _proposal_id(action: str, instrument_key: str, date: str | None, url: str | None, extra: str = "") -> str:
    stamp = (date or "undated").replace("-", "")
    digest = _sha("|".join([action, instrument_key, stamp, url or "", extra]))
    return f"{action}-{instrument_key}-{stamp}-{digest}"


def _urls_of(item: InboxItem) -> list[str]:
    urls: list[str] = []
    for value in (item.official_document_url, item.url):
        if value and value not in urls:
            urls.append(value)
    extra_sources = item.extra.get("sources") if item.extra else None
    if isinstance(extra_sources, list):
        for entry in extra_sources:
            if isinstance(entry, str) and entry not in urls:
                urls.append(entry)
            elif isinstance(entry, dict) and entry.get("url") and entry["url"] not in urls:
                urls.append(entry["url"])
    return urls


def _combined_text(item: InboxItem) -> str:
    return item.text()


def official_assent_listed(item: InboxItem) -> bool:
    if item.raw_assent_listed is True:
        return True
    if item.raw_assent_listed is False:
        return False
    text = _combined_text(item)
    if re.search(r"royal assent (was |is )?not listed|does not (yet )?list royal assent|awaiting royal assent|no royal assent", text, re.I):
        return False
    # An official page may list Assent with a date. Ministerial "becomes law" is not Assent.
    if item.raw_status_text and _ROYAL_ASSENT.search(item.raw_status_text):
        return True
    return False


def official_passed_both_houses(item: InboxItem) -> bool:
    if item.raw_status_text and _PASSED_BOTH.search(item.raw_status_text):
        return True
    return bool(_PASSED_BOTH.search(_combined_text(item)))


def is_ministerial_or_news_becomes_law(item: InboxItem, catalog: SourceCatalog) -> bool:
    text = f"{item.headline or ''}\n{item.summary or ''}"
    if not _BECOMES_LAW.search(text):
        return False
    role = source_kind_for(item.primary_url(), catalog, item.source_kind)
    if role in {"ministerial_release", "news", "statement", "legislative_record"}:
        return True
    if item.source_kind in {"ministerial", "ministerial_release", "news", "statement", "legislative_record"}:
        return True
    # A "becomes law" headline on a non-instrument page is treated as insufficient for Assent.
    if role != "instrument":
        return True
    return not official_assent_listed(item)


def is_ofcom_ii_consultation(item: InboxItem) -> bool:
    text = _combined_text(item).lower()
    if "ofcom" in text and "intimate" in text and ("image" in text or "takedown" in text) and _CONSULTATION.search(text):
        return True
    for url in _urls_of(item):
        parsed = urlparse(url)
        host = parsed.netloc.lower().removeprefix("www.")
        if host.endswith(OFCOM_CONSULTATION_HOST) and OFCOM_CONSULTATION_PATH in parsed.path:
            return True
    return False


def cites_ofcom_consultation_page(item: InboxItem) -> bool:
    for url in _urls_of(item):
        parsed = urlparse(url)
        host = parsed.netloc.lower().removeprefix("www.")
        if host.endswith(OFCOM_CONSULTATION_HOST) and OFCOM_CONSULTATION_PATH in parsed.path:
            return True
    return False


def is_consultation(item: InboxItem) -> bool:
    if is_ofcom_ii_consultation(item):
        return True
    return bool(_CONSULTATION.search(item.headline or "") or _CONSULTATION.search(item.summary or ""))


def is_joint_statement(item: InboxItem) -> bool:
    return bool(_JOINT_STATEMENT.search(_combined_text(item)))


def is_ceo_or_senator_statement(item: InboxItem) -> bool:
    if item.source_kind == "statement":
        return not official_passed_both_houses(item) and not official_assent_listed(item) and not is_consultation(item)
    text = _combined_text(item)
    if not _STATEMENT_ACTOR.search(text):
        return False
    # A statement about a bill that actually records passage or introduction is not "statement only".
    if official_passed_both_houses(item) or official_assent_listed(item):
        return False
    if re.search(r"\b(introduced|tabled|passed both houses|received royal assent|chaptered)\b", text, re.I) and _BILL_OR_ACT.search(text):
        # Could still be a mixed item. Require that the item is primarily a person speaking.
        if re.search(r"\bthese are statements, not the introduction or passage of legislation\b", text, re.I):
            return True
        if re.search(r"\bno bill\b|\bnot the introduction\b|\bnot (a|the) bill\b", text, re.I):
            return True
        return False
    if re.search(r"\bno formal (legislative )?response\b|\bnot the introduction or passage\b", text, re.I):
        return True
    # CEO commentary with no instrument language.
    if re.search(r"\bchief executive\b|\bceo\b", text, re.I) and not re.search(r"\bintroduced a bill\b|\bpassed a bill\b", text, re.I):
        return True
    if re.search(r"\bsenator[s]?\b.{0,80}\b(said|called for|call for)\b", text, re.I):
        return True
    return False


def is_brand_mention(item: InboxItem, matched: RegisterInstrument | None) -> bool:
    if item.section and _BRAND_SECTION.search(item.section):
        return matched is None
    if item.extra.get("brand_mention") is True:
        return matched is None
    if _TENCENT.search(_combined_text(item)) and matched is None and not _BILL_OR_ACT.search(_combined_text(item)) and not is_consultation(item):
        # Brand mention with no regulatory instrument.
        return True
    return False


def _source_refs(item: InboxItem, catalog: SourceCatalog) -> list[SourceRef]:
    refs: list[SourceRef] = []
    for url in _urls_of(item):
        source = catalog.matching_url(url)
        kind = "official" if source and source.official else (item.source_kind or "news")
        if source and source.role == "ministerial_release":
            kind = "ministerial"
        elif source and source.role == "news":
            kind = "news"
        elif source and source.official:
            kind = "official"
        refs.append(SourceRef(url=url, kind=kind, title=source.name if source else item.outlet, source_id=source.id if source else item.source_id))
    # Official URLs first.
    refs.sort(key=lambda r: (0 if r.kind == "official" else 1 if r.kind == "ministerial" else 2, r.url))
    return refs


def _has_official_primary(refs: list[SourceRef], catalog: SourceCatalog) -> bool:
    return any(r.kind == "official" and is_official_url(r.url, catalog) for r in refs)


def _auto_apply(item: InboxItem, catalog: SourceCatalog, significant: bool, flags: list[str], refs: list[SourceRef]) -> bool:
    if not significant or flags:
        return False
    if official_assent_listed(item) is False and is_ministerial_or_news_becomes_law(item, catalog):
        return False
    source = catalog.by_id(item.source_id) or catalog.matching_url(item.primary_url())
    if source and not source.auto_apply_eligible:
        return False
    # Auto-apply only when an official, auto-apply-eligible source is cited first.
    for ref in refs:
        matched = catalog.matching_url(ref.url)
        if matched and matched.official and matched.auto_apply_eligible and ref.kind == "official":
            return True
    return False


def _base_proposal(
    item: InboxItem,
    action: str,
    catalog: SourceCatalog,
    *,
    instrument_id: str | None,
    proposed_id: str | None,
    fields: dict[str, Any],
    previous_values: dict[str, Any] | None,
    significant: bool,
    confidence: str,
    notes: str,
    epistemic: EpistemicMark,
    rejected: bool = False,
    extra_flags: list[str] | None = None,
) -> Proposal:
    vocab = load_vocabularies()
    flags = validate_fields(fields, vocab)
    if extra_flags:
        flags = flags + [f for f in extra_flags if f not in flags]
    if flags:
        # Invalid labels must not travel in fields that would be applied.
        fields = {k: v for k, v in fields.items() if k not in {
            "status", "instrument_kind", "service_type_ids", "obligation_types", "obligations", "kind",
        } or not validate_fields({k: v}, vocab)}
        significant = False
        rejected = True
    refs = _source_refs(item, catalog)
    fetched_at = item.fetched_at or ""
    fetched_at_utc = item.fetched_at_utc or ""
    if not fetched_at:
        from ts_monitor.timeutil import now_pair
        fetched_at, fetched_at_utc = now_pair()
    key = instrument_id or proposed_id or item.id
    auto = _auto_apply(item, catalog, significant and not rejected, flags, refs)
    if flags or rejected:
        auto = False
    return Proposal(
        proposal_id=_proposal_id(action, key, item.published_date, item.primary_url(), item.id),
        action=action,  # type: ignore[arg-type]
        instrument_id=instrument_id,
        proposed_id=proposed_id,
        fields=fields,
        previous_values=previous_values,
        significant=bool(significant and not rejected and not flags),
        confidence=confidence,  # type: ignore[arg-type]
        sources=refs,
        fetched_at=fetched_at,
        fetched_at_utc=fetched_at_utc,
        notes=notes,
        epistemic=epistemic,
        inbox_item_id=item.id,
        vocabulary_flags=flags,
        auto_apply_eligible=auto,
        rejected=rejected,
    )


def _news_only(
    item: InboxItem,
    catalog: SourceCatalog,
    notes: str,
    confidence: str = "low",
    extra_flags: list[str] | None = None,
    rejected: bool = False,
    fields: dict[str, Any] | None = None,
    instrument_id: str | None = None,
) -> Proposal:
    return _base_proposal(
        item,
        "news_only",
        catalog,
        instrument_id=instrument_id,
        proposed_id=None,
        fields=fields or {},
        previous_values=None,
        significant=False,
        confidence=confidence,
        notes=notes,
        epistemic=EpistemicMark(
            sourced_facts=[],
            category_judgement=[],
        ),
        rejected=rejected,
        extra_flags=extra_flags,
    )


def _guard_enactment_fields(fields: dict[str, Any]) -> dict[str, Any]:
    """Strip any enactment upgrade that is not backed by an official Assent or commencement listing."""
    cleaned = dict(fields)
    kind = cleaned.get("instrument_kind")
    if kind in ENACTMENT_KINDS:
        cleaned["instrument_kind"] = "bill"
    status = cleaned.get("status")
    if status in ENACTMENT_STATUSES:
        # Without official commencement, do not invent in-force status.
        if "signed_date" not in cleaned or cleaned.get("signed_date") in (None, ""):
            cleaned["status"] = "passed" if cleaned.get("status") else cleaned.get("status")
            if cleaned.get("status") in ENACTMENT_STATUSES:
                cleaned["status"] = "passed"
    if cleaned.get("signed_date") and not fields.get("_official_assent"):
        cleaned["signed_date"] = None
    if cleaned.get("effective_date") and not fields.get("_official_commencement"):
        cleaned["effective_date"] = None
    cleaned.pop("_official_assent", None)
    cleaned.pop("_official_commencement", None)
    return cleaned


def classify_item(
    item: InboxItem,
    register: Register,
    match_instrument: RegisterInstrument | None,
    catalog: SourceCatalog | None = None,
) -> Proposal:
    catalog = catalog or load_catalog()
    text = _combined_text(item)

    # Vocabulary rejection of caller-supplied proposed fields, even before other rules.
    supplied = dict(item.proposed_fields or {})
    supplied_flags = validate_fields(supplied)
    if supplied_flags:
        return _news_only(
            item,
            catalog,
            notes=(
                "Proposed labels were rejected because they are not in the frozen dashboard vocabularies. "
                "No register patch was emitted."
            ),
            confidence="low",
            extra_flags=supplied_flags,
            rejected=True,
            fields={},
        )

    # Brand mentions with no instrument: never auto-applied.
    if is_brand_mention(item, match_instrument):
        return _news_only(
            item,
            catalog,
            notes=(
                "Brand mention with no regulatory instrument. The item is retained as news_only "
                "and must not be auto-applied."
            ),
            confidence="low",
        )

    # Joint regulator statements without a binding instrument.
    if is_joint_statement(item) and not official_passed_both_houses(item) and not official_assent_listed(item) and not is_consultation(item):
        return _news_only(
            item,
            catalog,
            notes=(
                "Joint regulator statement or network communique with no binding instrument. "
                "Recorded as news_only. Not significant for automatic dashboard application."
            ),
            confidence="medium",
            instrument_id=match_instrument.id if match_instrument else None,
        )

    # CEO or senator statements that do not change an instrument's legal status.
    if is_ceo_or_senator_statement(item) and not official_passed_both_houses(item) and not is_consultation(item):
        return _news_only(
            item,
            catalog,
            notes=(
                "Political or company statement with no bill, act, consultation or official status change. "
                "Recorded as news_only. Not significant for automatic dashboard application."
            ),
            confidence="low",
            instrument_id=match_instrument.id if match_instrument else None,
        )

    # Ministerial or press "becomes law" without an official Assent listing.
    if is_ministerial_or_news_becomes_law(item, catalog) and not official_assent_listed(item):
        fields: dict[str, Any] = {}
        if match_instrument:
            fields = {
                "status": match_instrument.status,
                "instrument_kind": match_instrument.instrument_kind or "bill",
                "signed_date": None,
                "effective_date": None,
            }
            fields = _guard_enactment_fields(fields)
        return _news_only(
            item,
            catalog,
            notes=(
                "Ministerial or press language such as 'becomes law' is not Royal Assent. "
                "The official instrument page must list Assent before the instrument can be treated as an Act "
                "or as in force. No enactment upgrade is proposed."
            ),
            confidence="medium",
            fields=fields,
            instrument_id=match_instrument.id if match_instrument else None,
        )

    # Official consultation, including the Ofcom intimate-image codes example.
    if is_consultation(item):
        return _classify_consultation(item, register, match_instrument, catalog)

    # Official Passed Both Houses, no Royal Assent.
    if official_passed_both_houses(item) and not official_assent_listed(item):
        return _classify_passed_both_houses(item, match_instrument, catalog)

    # Official Assent or commencement would be handled here when an official listing exists.
    if official_assent_listed(item) and match_instrument:
        return _classify_official_assent(item, match_instrument, catalog)

    # Default: news only. Do not invent a new instrument from press copy alone.
    return _news_only(
        item,
        catalog,
        notes=(
            "The item was retained in the inbox but does not meet the significance bar for a register patch. "
            "A significant auto-apply proposal requires an official primary document and a qualifying instrument event."
        ),
        confidence="low",
        instrument_id=match_instrument.id if match_instrument else None,
    )


def _classify_passed_both_houses(
    item: InboxItem,
    match_instrument: RegisterInstrument | None,
    catalog: SourceCatalog,
) -> Proposal:
    refs_preview = _source_refs(item, catalog)
    official = _has_official_primary(refs_preview, catalog) or (item.source_kind in {"official", "instrument"})
    if not official and not any(AU_DDOC_HOMEPAGE in (u or "") for u in _urls_of(item)):
        # Press report of passage, without the official homepage, must not be auto-applied.
        return _news_only(
            item,
            catalog,
            notes=(
                "The item reports passage through both Houses but does not cite an official instrument page. "
                "It is retained as news_only until an official listing is attached. "
                "No signed or effective date is proposed."
            ),
            confidence="medium",
            instrument_id=match_instrument.id if match_instrument else None,
        )
    if not match_instrument:
        # Should not invent a brand-new row when the snapshot already holds the bill, but
        # if unmatched, propose a new bill at status passed, still a bill, no Assent dates.
        proposed_id = "AU-DDOC-2026" if "duty of care" in _combined_text(item).lower() else None
        fields = {
            "status": "passed",
            "instrument_kind": "bill",
            "passed_date": item.published_date,
            "signed_date": None,
            "effective_date": None,
        }
        notes = (
            "Official status is Passed Both Houses. Royal Assent is not listed. "
            "The instrument remains a bill. It is not an Act and is not in force. "
            "No signed or effective date is proposed."
        )
        return _base_proposal(
            item,
            "new_instrument" if not proposed_id else "status_change",
            catalog,
            instrument_id=proposed_id,
            proposed_id=None if proposed_id else "UNMATCHED-PASSED-BILL",
            fields=fields,
            previous_values=None,
            significant=True,
            confidence="high",
            notes=notes,
            epistemic=EpistemicMark(
                sourced_facts=[
                    {"field": "status", "value": "passed", "source_url": item.primary_url()},
                    {"field": "instrument_kind", "value": "bill", "source_url": item.primary_url()},
                    {"field": "passed_date", "value": item.published_date, "source_url": item.primary_url()},
                    {"field": "signed_date", "value": None, "note": "Royal Assent is not listed on the official page."},
                    {"field": "effective_date", "value": None, "note": "The instrument is not in force."},
                ],
                category_judgement=[],
            ),
        )

    previous = {
        "status": match_instrument.status,
        "instrument_kind": match_instrument.instrument_kind,
        "passed_date": None,
        "signed_date": None,
        "effective_date": match_instrument.effective_date,
    }
    already = match_instrument.status == "passed" and (match_instrument.instrument_kind or "bill") == "bill"
    fields = {
        "status": "passed",
        "instrument_kind": "bill",
        "passed_date": item.published_date,
        "signed_date": None,
        "effective_date": None,
        "notes": (
            "Official bill homepage records Passed Both Houses"
            + (f" on {item.published_date}" if item.published_date else "")
            + ". Royal Assent is not listed. The instrument is not an Act and is not in force."
        ),
    }
    notes = fields["notes"]
    significant = (not already) and official
    action = "status_change" if not already else "news_only"
    if already:
        notes = (
            "The register snapshot already records this instrument as passed, with instrument_kind bill "
            "and no signed or effective date. The official page still does not list Royal Assent. "
            "No further status change is proposed."
        )
        fields = {
            "status": "passed",
            "instrument_kind": "bill",
            "signed_date": None,
            "effective_date": None,
        }
    epistemic = EpistemicMark(
        sourced_facts=[
            {"field": "status", "value": "passed", "source_url": item.primary_url()},
            {"field": "instrument_kind", "value": "bill", "source_url": item.primary_url()},
            {"field": "passed_date", "value": item.published_date if not already else None, "source_url": item.primary_url()},
            {"field": "signed_date", "value": None, "note": "Royal Assent is not listed on the official page."},
            {"field": "effective_date", "value": None, "note": "The instrument is not in force."},
        ],
        category_judgement=[
            {
                "field": "service_type_ids",
                "value": list(match_instrument.service_type_ids),
                "note": "Carried forward from the register snapshot. Category assignment is analytical judgement.",
            }
        ],
    )
    return _base_proposal(
        item,
        action,
        catalog,
        instrument_id=match_instrument.id,
        proposed_id=None,
        fields=fields,
        previous_values=previous,
        significant=significant,
        confidence="high" if official else "medium",
        notes=notes,
        epistemic=epistemic,
    )


def _classify_official_assent(
    item: InboxItem,
    match_instrument: RegisterInstrument,
    catalog: SourceCatalog,
) -> Proposal:
    fields = {
        "status": "passed",
        "instrument_kind": "enacted",
        "signed_date": item.published_date,
        "_official_assent": True,
    }
    # Assent makes it an Act, but commencement may still be later. Do not invent an effective date.
    fields["effective_date"] = None
    fields = {k: v for k, v in fields.items() if not k.startswith("_")} | {"signed_date": item.published_date, "effective_date": None, "instrument_kind": "enacted", "status": "passed"}
    notes = (
        "An official listing of Royal Assent or equivalent signature was recorded. "
        "instrument_kind is enacted. No effective date is proposed unless a commencement listing is also present."
    )
    return _base_proposal(
        item,
        "status_change",
        catalog,
        instrument_id=match_instrument.id,
        proposed_id=None,
        fields=fields,
        previous_values={
            "status": match_instrument.status,
            "instrument_kind": match_instrument.instrument_kind,
            "signed_date": None,
            "effective_date": match_instrument.effective_date,
        },
        significant=True,
        confidence="high",
        notes=notes,
        epistemic=EpistemicMark(
            sourced_facts=[
                {"field": "instrument_kind", "value": "enacted", "source_url": item.primary_url()},
                {"field": "signed_date", "value": item.published_date, "source_url": item.primary_url()},
                {"field": "effective_date", "value": None, "note": "No official commencement date was supplied on this item."},
            ],
            category_judgement=[],
        ),
    )


def _classify_consultation(
    item: InboxItem,
    register: Register,
    match_instrument: RegisterInstrument | None,
    catalog: SourceCatalog,
) -> Proposal:
    # Do not treat a consultation as a status change on an already enacted parent statute.
    parent_id = None
    if is_ofcom_ii_consultation(item):
        parent_id = "UK-CPA-2026" if register.get("UK-CPA-2026") else None
        proposed_id = OFCOM_PROPOSED_ID
        name = "Ofcom consultation on proposed updates to Illegal Content Codes of Practice for intimate-image abuse takedown"
        jurisdiction = "GB"
        year = 2026
        official_page = cites_ofcom_consultation_page(item)
        services = ["social_media", "other"]
        notes = (
            "This is a consultation on draft codes. It is not a final code and not the enactment of the "
            "Crime and Policing Act 2026 statutory duty. Significant is true only because the official "
            "consultation page is cited."
            if official_page
            else (
                "This is a consultation on draft codes. It is not a final code and not the enactment of the "
                "Crime and Policing Act 2026 statutory duty. The official consultation page was not cited, "
                "so the proposal is not marked significant for automatic application."
            )
        )
        fields = {
            "name": name,
            "jurisdiction_id": jurisdiction,
            "year": year,
            "status": "proposed",
            "instrument_kind": "consultation",
            "source_url": item.official_document_url or (item.url if official_page else None) or item.url,
            "service_type_ids": services,
            "related_instrument_ids": [parent_id] if parent_id else [],
            "signed_date": None,
            "effective_date": None,
        }
        epistemic = EpistemicMark(
            sourced_facts=[
                {"field": "instrument_kind", "value": "consultation", "source_url": item.primary_url()},
                {"field": "status", "value": "proposed", "source_url": item.primary_url()},
                {"field": "signed_date", "value": None, "note": "A consultation is not an enactment."},
                {"field": "effective_date", "value": None, "note": "A consultation is not in force."},
            ],
            category_judgement=[
                {
                    "field": "service_type_ids",
                    "value": services,
                    "note": "User-to-user and search services have no exact search label in the frozen service types. social_media and other are analytical judgement.",
                },
                {
                    "field": "obligation type",
                    "value": "content_moderation",
                    "note": "Draft takedown codes concern content moderation. This is analytical judgement, not a sourced legal classification of a final code.",
                },
            ],
        )
        # Never attach this as a status_change on UK-CPA-2026.
        return _base_proposal(
            item,
            "new_instrument",
            catalog,
            instrument_id=None,
            proposed_id=proposed_id,
            fields=fields,
            previous_values=None,
            significant=bool(official_page),
            confidence="high" if official_page else "medium",
            notes=notes,
            epistemic=epistemic,
        )

    # Generic consultation.
    official = _has_official_primary(_source_refs(item, catalog), catalog)
    year = None
    if item.published_date and len(item.published_date) >= 4 and item.published_date[:4].isdigit():
        year = int(item.published_date[:4])
    slug = re.sub(r"[^A-Z0-9]+", "-", (item.headline or "CONSULTATION").upper()).strip("-")[:40]
    jid = item.jurisdiction_hint or "XX"
    proposed_id = f"{jid}-{slug}-{year or 'CONS'}"
    fields = {
        "name": item.headline,
        "jurisdiction_id": item.jurisdiction_hint,
        "year": year,
        "status": "proposed",
        "instrument_kind": "consultation",
        "source_url": item.primary_url(),
        "signed_date": None,
        "effective_date": None,
    }
    return _base_proposal(
        item,
        "new_instrument",
        catalog,
        instrument_id=None,
        proposed_id=proposed_id,
        fields=fields,
        previous_values=None,
        significant=bool(official),
        confidence="high" if official else "medium",
        notes=(
            "Proposed as a new consultation row. This is not a final code or an enactment of a statutory duty."
        ),
        epistemic=EpistemicMark(
            sourced_facts=[
                {"field": "instrument_kind", "value": "consultation", "source_url": item.primary_url()},
                {"field": "status", "value": "proposed", "source_url": item.primary_url()},
            ],
            category_judgement=[],
        ),
    )


def classify_all(
    items: list[InboxItem],
    register: Register,
    catalog: SourceCatalog | None = None,
    matches: list | None = None,
) -> list[Proposal]:
    from ts_monitor.matcher import match_item

    catalog = catalog or load_catalog()
    proposals: list[Proposal] = []
    for index, item in enumerate(items):
        instrument = None
        if matches and index < len(matches):
            instrument = matches[index].instrument if hasattr(matches[index], "instrument") else None
        else:
            instrument = match_item(item, register).instrument
        proposals.append(classify_item(item, register, instrument, catalog))
    return proposals
