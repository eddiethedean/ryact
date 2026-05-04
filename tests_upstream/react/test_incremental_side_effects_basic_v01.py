from __future__ import annotations

from ryact.concurrent import start_transition


def test_start_transition_symbol_exists() -> None:
    # Minimal acceptance slice: surface exists; deeper semantics reopened.
    assert callable(start_transition)

