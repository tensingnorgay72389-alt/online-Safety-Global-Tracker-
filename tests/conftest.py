from __future__ import annotations

from pathlib import Path

import pytest

from ts_monitor.register import load_register
from ts_monitor.sources import load_catalog

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"
PRE_REGISTER = FIXTURES / "register_pre_ddoc_passage.json"


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES


@pytest.fixture
def pre_register():
    return load_register(PRE_REGISTER)


@pytest.fixture
def current_register():
    return load_register(ROOT / "data" / "register_snapshot.json")


@pytest.fixture
def catalog():
    return load_catalog(ROOT / "config" / "sources.yaml")
