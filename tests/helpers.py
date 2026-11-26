from __future__ import annotations

from pathlib import Path

from ts_monitor.classifiers import classify_item
from ts_monitor.matcher import match_item
from ts_monitor.parsers import load_items_file
from ts_monitor.register import Register
from ts_monitor.sources import SourceCatalog

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def load_fixture_item(name: str):
    path = FIXTURES / "inbox" / name
    items = load_items_file(path)
    assert len(items) == 1, f"expected one item in {name}"
    return items[0]


def classify_fixture(name: str, register: Register, catalog: SourceCatalog):
    item = load_fixture_item(name)
    match = match_item(item, register)
    proposal = classify_item(item, register, match.instrument, catalog)
    return item, match, proposal
