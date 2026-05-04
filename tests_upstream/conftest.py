"""Expose repo `scripts/` on sys.path so tests can import scheduler_jest_extract."""

from __future__ import annotations

import sys
from collections.abc import Iterator
from pathlib import Path

import pytest
from ryact.act import set_act_environment_enabled
from ryact.dev import set_dev

_scripts = Path(__file__).resolve().parents[1] / "scripts"
if str(_scripts) not in sys.path:
    sys.path.insert(0, str(_scripts))


@pytest.fixture(autouse=True)
def _reset_ryact_dev_mode_after_test() -> Iterator[None]:
    """Many burndown tests toggle DEV; restore default so unrelated tests stay deterministic."""
    yield
    set_dev(True)


@pytest.fixture(autouse=True)
def _reset_ryact_act_environment_after_test() -> Iterator[None]:
    """Prevent cross-test leakage of act environment globals."""
    yield
    set_act_environment_enabled(False)


@pytest.fixture(autouse=True)
def ensure_greenlet_context() -> Iterator[None]:
    """
    Some environments auto-register an async autouse fixture named
    ``ensure_greenlet_context`` via third-party plugins.

    Our upstream translation tests are synchronous; provide a no-op sync fixture with
    the same name to avoid pytest-asyncio strict-mode warnings.
    """
    yield
