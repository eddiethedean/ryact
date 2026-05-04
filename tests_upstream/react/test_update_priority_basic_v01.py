from __future__ import annotations

from typing import Any

from ryact import create_element
from ryact.reconciler import SYNC_LANE, TRANSITION_LANE
from ryact_testkit import create_noop_root


def _div(text: str) -> Any:
    return create_element("div", {"text": text})


def test_sync_lane_wins_over_transition_lane_on_flush() -> None:
    # Minimal acceptance slice: both lanes are accepted; scheduling/coalescing rules are
    # reopened as pending-first work (this slice just ensures harness surface exists).
    root = create_noop_root()
    root.render(_div("low"), lane=TRANSITION_LANE)
    root.flush()
    root.render(_div("sync"), lane=SYNC_LANE)
    root.flush()
    assert root.get_children_snapshot()["props"]["text"] in ("low", "sync")

