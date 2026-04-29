from __future__ import annotations

from typing import Any

from ryact import create_element
from ryact_testkit import create_noop_root


def _text(value: str) -> Any:
    return create_element("div", {"text": value})


def test_can_cancel_partially_rendered_work_and_restart() -> None:
    # Upstream: ReactIncremental-test.js
    # "can cancel partially rendered work and restart"
    #
    # This is a minimal harness-level translation:
    # - We force a yield during render so the first update does not commit.
    # - We schedule a new update (representing "restart") and then flush to completion.
    root = create_noop_root(yield_after_nodes=1)

    root.render(_text("A"))
    root.flush()
    assert root.get_children_snapshot() is None

    # Cancel/restart with a different payload.
    root.render(_text("B"))
    root.set_yield_after_nodes(0)
    root.flush()

    assert root.get_children_snapshot() == {
        "type": "div",
        "key": None,
        "props": {"text": "B"},
        "children": [],
    }

