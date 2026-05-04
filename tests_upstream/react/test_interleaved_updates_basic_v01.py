from __future__ import annotations

from ryact.reconciler import SYNC_LANE, TRANSITION_LANE


def test_lanes_exist_for_interleaved_update_work() -> None:
    assert SYNC_LANE is not None
    assert TRANSITION_LANE is not None

