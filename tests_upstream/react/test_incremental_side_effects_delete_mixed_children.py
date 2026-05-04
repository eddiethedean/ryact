from __future__ import annotations

from collections.abc import Callable
from typing import cast

from ryact import Component, create_element, use_state
from ryact_testkit import create_noop_root


class Inner(Component):
    def render(self) -> object:
        return create_element("span", {"text": "c"})


def test_can_clear_mixed_text_host_and_component_children() -> None:
    # Upstream: ReactIncrementalSideEffects-test.js
    # "can deletes children either components, host or text"
    api: dict[str, object] = {}

    def App() -> object:
        full, set_full = use_state(True)
        api["set"] = set_full
        if not full:
            return create_element("div", None)
        return create_element(
            "div",
            None,
            "txt",
            create_element("b", {"text": "h"}),
            create_element(Inner),
        )

    root = create_noop_root()
    root.render(create_element(App))
    snap = root.container.last_committed
    assert snap["type"] == "div"
    assert len(snap["children"]) == 3
    assert snap["children"][0] == "txt"
    assert snap["children"][1] == {
        "type": "b",
        "key": None,
        "props": {"text": "h"},
        "children": [],
    }
    assert snap["children"][2] == {
        "type": "span",
        "key": None,
        "props": {"text": "c"},
        "children": [],
    }
    cast(Callable[[bool], None], api["set"])(False)
    root.flush()
    assert root.container.last_committed == {
        "type": "div",
        "key": None,
        "props": {},
        "children": [],
    }
