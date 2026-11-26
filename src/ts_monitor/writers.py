"""Write inbox items, proposals and significant patches as deterministic JSON."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ts_monitor.models import FetchError, InboxItem, Proposal


def dump(data: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def write_inbox(items: list[InboxItem], out_dir: Path) -> Path:
    inbox_dir = out_dir / "inbox"
    inbox_dir.mkdir(parents=True, exist_ok=True)
    payload = [item.to_dict() for item in items]
    path = inbox_dir / "items.json"
    dump(payload, path)
    return path


def write_fetch_errors(errors: list[FetchError], out_dir: Path) -> Path | None:
    if not errors:
        return None
    path = out_dir / "inbox" / "fetch_errors.json"
    dump([error.to_dict() for error in errors], path)
    return path


def write_proposals(proposals: list[Proposal], out_dir: Path) -> tuple[Path, Path | None]:
    proposals_dir = out_dir / "proposals"
    significant_dir = out_dir / "significant"
    proposals_dir.mkdir(parents=True, exist_ok=True)
    significant_dir.mkdir(parents=True, exist_ok=True)
    all_payload = [proposal.to_dict() for proposal in proposals]
    all_path = proposals_dir / "proposals.json"
    dump(all_payload, all_path)
    significant = [
        proposal.to_dict()
        for proposal in proposals
        if proposal.significant and proposal.auto_apply_eligible and not proposal.rejected
    ]
    sig_path = significant_dir / "proposals.json"
    dump(significant, sig_path)
    # Also write one file per significant proposal for easier operator review.
    for proposal in proposals:
        if proposal.significant and proposal.auto_apply_eligible and not proposal.rejected:
            dump(proposal.to_dict(), significant_dir / f"{proposal.proposal_id}.json")
    return all_path, sig_path if significant else sig_path
