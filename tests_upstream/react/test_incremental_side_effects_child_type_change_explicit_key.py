from __future__ import annotations

from typing import Callable, cast

from ryact import create_element, use_state
from ryact_testkit import create_noop_root


def test_host_child_changes_tag_with_explicit_key() -> None:
    # Upstream: ReactIncrementalSideEffects-test.js
    # "can delete a child that changes type - explicit keys"
    api: dict[str, object] = {}

    def App() -> object:
        use_span, set_use_span = use_state(True)
        api["set"] = set_use_span
        if use_span:
            return create_element(
                "div",
                None,
                create_element("span", {"key": "x", "text": "s"}),
            )
        return create_element(
            "div",
            None,
            create_element("p", {"key": "x", "text": "p"}),
        )

    root = create_noop_root()
    root.render(create_element(App))
    assert root.container.last_committed == {
        "type": "div",
        "key": None,
        "props": {},
        "children": [
            {"type": "span", "key": "x", "props": {"text": "s"}, "children": []},
        ],
    }
    cast(Callable[[bool], None], api["set"])(False)
    root.flush()
    assert root.container.last_committed == {
        "type": "div",
        "key": None,
        "props": {},
        "children": [
            {"type": "p", "key": "x", "props": {"text": "p"}, "children": []},
        ],
    }
