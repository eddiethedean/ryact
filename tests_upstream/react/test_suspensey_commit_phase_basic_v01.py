from __future__ import annotations

from ryact.concurrent import Thenable


def test_thenable_symbol_is_exposed_for_suspensey_work() -> None:
    # Minimal acceptance slice: Thenable surface exists for Suspensey paths.
    assert Thenable is not None

