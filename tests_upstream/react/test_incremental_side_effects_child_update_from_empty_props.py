from __future__ import annotations

from typing import Callable, cast

from ryact import create_element, use_state
from ryact_testkit import create_noop_root


def test_updates_host_child_when_prior_props_empty() -> None:
    # Upstream: ReactIncrementalSideEffects-test.js
    # "updates a child even though the old props is empty"
    api: dict[str, object] = {}

    def App() -> object:
        on, set_on = use_state(False)
        api["set"] = set_on
        inner = create_element("span", {}) if not on else create_element("span", {"text": "x"})
        return create_element("div", None, inner)

    root = create_noop_root()
    root.render(create_element(App))
    assert root.container.last_committed == {
        "type": "div",
        "key": None,
        "props": {},
        "children": [
            {"type": "span", "key": None, "props": {}, "children": []},
        ],
    }
    cast(Callable[[bool], None], api["set"])(True)
    root.flush()
    assert root.container.last_committed == {
        "type": "div",
        "key": None,
        "props": {},
        "children": [
            {"type": "span", "key": None, "props": {"text": "x"}, "children": []},
        ],
    }
