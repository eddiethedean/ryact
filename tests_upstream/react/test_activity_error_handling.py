from __future__ import annotations

from typing import Any

from ryact import create_element
from ryact.concurrent import activity
from ryact_testkit import create_noop_root


def test_errors_inside_hidden_activity_do_not_escape_visible_ui() -> None:
    """
    Upstream: ActivityErrorHandling-test.js
    - errors inside a hidden Activity do not escape in the visible part of the UI
    """
    root = create_noop_root()

    def Boom(**_: Any) -> Any:
        raise RuntimeError("boom")

    tree = create_element(
        "div",
        {
            "children": (
                create_element("span", {"id": "visible"}),
                create_element(
                    activity,
                    {"mode": "hidden", "children": create_element(Boom, {})},
                ),
            )
        },
    )
    root.render(tree)
    snap = root.get_children_snapshot()
    assert isinstance(snap, dict)
    assert snap["type"] == "div"
    # Hidden activity contributes no visible committed output.
    assert snap["children"][0]["type"] == "span"
