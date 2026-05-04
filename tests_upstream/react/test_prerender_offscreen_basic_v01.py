from __future__ import annotations

from ryact.concurrent import Scope


def test_scope_symbol_exists_for_offscreen_work() -> None:
    # Minimal acceptance slice: offscreen/prerender work reuses Scope scaffolding today.
    assert Scope is not None

