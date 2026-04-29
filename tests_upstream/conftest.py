"""Expose repo `scripts/` on sys.path so tests can import scheduler_jest_extract."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from ryact.dev import set_dev

_scripts = Path(__file__).resolve().parents[1] / "scripts"
if str(_scripts) not in sys.path:
    sys.path.insert(0, str(_scripts))


@pytest.fixture(autouse=True)
def _reset_ryact_dev_mode_after_test() -> None:
    """Many burndown tests toggle DEV; restore default so unrelated tests stay deterministic."""
    yield
    set_dev(True)
