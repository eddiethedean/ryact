from __future__ import annotations

from collections.abc import Callable
from typing import cast

from ryact import create_element, use_state
from ryact_testkit import create_noop_root


def test_host_child_changes_tag_with_implicit_position_keys() -> None:
    # Upstream: ReactIncrementalSideEffects-test.js
    # "can delete a child that changes type - implicit keys"
    api: dict[str, object] = {}

    def App() -> object:
        use_span, set_use_span = use_state(True)
        api["set"] = set_use_span
        if use_span:
            return create_element(
                "div",
                None,
                create_element("span", {"text": "s"}),
            )
        return create_element(
            "div",
            None,
            create_element("p", {"text": "p"}),
        )

    root = create_noop_root()
    root.render(create_element(App))
    assert root.container.last_committed == {
        "type": "div",
        "key": None,
        "props": {},
        "children": [
            {"type": "span", "key": None, "props": {"text": "s"}, "children": []},
        ],
    }
    cast(Callable[[bool], None], api["set"])(False)
    root.flush()
    assert root.container.last_committed == {
        "type": "div",
        "key": None,
        "props": {},
        "children": [
            {"type": "p", "key": None, "props": {"text": "p"}, "children": []},
        ],
    }
