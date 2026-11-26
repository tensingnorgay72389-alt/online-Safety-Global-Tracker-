"""Shared pipeline used by the CLI commands."""

from __future__ import annotations

from pathlib import Path

from ts_monitor.classifiers import classify_all
from ts_monitor.fetchers import Fetcher
from ts_monitor.matcher import match_all
from ts_monitor.models import FetchError, InboxItem, Proposal
from ts_monitor.parsers import load_items_file
from ts_monitor.register import Register, load_register
from ts_monitor.sources import SourceCatalog, load_catalog
from ts_monitor.writers import write_fetch_errors, write_inbox, write_proposals


def ingest_path(path: Path) -> list[InboxItem]:
    return load_items_file(path)


def run_pipeline(
    items: list[InboxItem],
    register: Register,
    catalog: SourceCatalog,
    out_dir: Path,
    errors: list[FetchError] | None = None,
) -> list[Proposal]:
    paired = match_all(items, register)
    proposals = classify_all(items, register, catalog, matches=[match for _, match in paired])
    write_inbox(items, out_dir)
    write_proposals(proposals, out_dir)
    if errors:
        write_fetch_errors(errors, out_dir)
    return proposals


def load_context(register_path: Path | None, sources_path: Path | None) -> tuple[Register, SourceCatalog]:
    catalog = load_catalog(sources_path) if sources_path else load_catalog()
    # load_catalog is lru-cached on the path string. Passing None uses the default.
    if sources_path:
        catalog = load_catalog(str(sources_path))
    register = load_register(register_path)
    return register, catalog
