"""Resolve repository paths from the environment, the current directory or the package location."""

from __future__ import annotations

import os
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
SRC_DIR = PACKAGE_DIR.parent
REPO_CANDIDATES = (
    Path(os.environ["TS_MONITOR_ROOT"]).resolve() if os.environ.get("TS_MONITOR_ROOT") else None,
    Path.cwd().resolve(),
    SRC_DIR.parent.resolve(),
)


def repo_root() -> Path:
    for candidate in REPO_CANDIDATES:
        if candidate is None:
            continue
        if (candidate / "config" / "sources.yaml").is_file() and (candidate / "data").is_dir():
            return candidate
    return SRC_DIR.parent.resolve()


def config_dir() -> Path:
    return repo_root() / "config"


def data_dir() -> Path:
    return repo_root() / "data"


def default_register_path() -> Path:
    return data_dir() / "register_snapshot.json"


def default_sources_path() -> Path:
    return config_dir() / "sources.yaml"


def default_vocabularies_path() -> Path:
    return config_dir() / "vocabularies.yaml"


def default_regulators_path() -> Path:
    return config_dir() / "regulators.yaml"


def default_out_dir() -> Path:
    return repo_root() / "out"
