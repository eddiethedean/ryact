from __future__ import annotations

from ryact.hooks import use_deferred_value


def test_use_deferred_value_symbol_exists() -> None:
    # Minimal acceptance slice: hook surface exists; deeper semantics are reopened.
    assert callable(use_deferred_value)

