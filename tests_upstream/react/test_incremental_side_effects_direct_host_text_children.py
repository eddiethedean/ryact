from __future__ import annotations

from typing import Callable, cast

from ryact import create_element, use_state
from ryact_testkit import create_noop_root


def test_can_update_string_children_of_host_element() -> None:
    # Upstream: ReactIncrementalSideEffects-test.js
    # "can update child nodes rendering into text nodes"
    api: dict[str, object] = {}

    def App() -> object:
        label, set_label = use_state("a")
        api["set"] = set_label
        return create_element("div", None, label)

    root = create_noop_root()
    root.render(create_element(App))
    assert root.container.last_committed == {
        "type": "div",
        "key": None,
        "props": {},
        "children": ["a"],
    }
    cast(Callable[[str], None], api["set"])("b")
    root.flush()
    assert root.container.last_committed == {
        "type": "div",
        "key": None,
        "props": {},
        "children": ["b"],
    }
