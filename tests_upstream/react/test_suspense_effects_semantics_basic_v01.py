from __future__ import annotations

from typing import Any

from ryact.concurrent import Suspense


def test_suspense_symbol_is_exposed() -> None:
    # Minimal acceptance slice: the Suspense symbol exists (noop renderer does not model
    # Suspense semantics yet; those are reopened as pending-first work).
    assert Suspense is not None

