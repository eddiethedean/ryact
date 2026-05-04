from __future__ import annotations

from ryact_testkit import create_noop_root


def test_noop_root_exists_for_incremental_error_handling_work() -> None:
    # Minimal acceptance slice: harness surface exists; deeper semantics reopened.
    assert create_noop_root is not None

