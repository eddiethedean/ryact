from __future__ import annotations

from collections.abc import Callable
from typing import cast

from ryact import create_element, use_state
from ryact_testkit import create_noop_root


def test_can_update_text_child_under_host_element() -> None:
    # Upstream: ReactIncrementalSideEffects-test.js
    # "can update child nodes of a host instance"
    api: dict[str, object] = {}

    def App() -> object:
        label, set_label = use_state("a")
        api["set"] = set_label
        return create_element("div", None, create_element("span", None, label))

    root = create_noop_root()
    root.render(create_element(App))
    assert root.container.last_committed == {
        "type": "div",
        "key": None,
        "props": {},
        "children": [
            {
                "type": "span",
                "key": None,
                "props": {},
                "children": ["a"],
            },
        ],
    }
    cast(Callable[[str], None], api["set"])("z")
    root.flush()
    assert root.container.last_committed_as_dict()["children"][0]["children"] == ["z"]
