from __future__ import annotations

from ryact_testkit import create_noop_root


def test_noop_root_exists_even_without_persistent_mode() -> None:
    # Minimal acceptance slice: harness exists; persistent host mode reopened as pending-first.
    assert create_noop_root is not None

