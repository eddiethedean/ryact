from __future__ import annotations

from typing import Callable, cast

from ryact import Fragment, create_element, use_state
from ryact_testkit import create_noop_root


def test_can_update_child_nodes_of_a_fragment() -> None:
    # Upstream: ReactIncrementalSideEffects-test.js — "can update child nodes of a fragment"
    api: dict[str, Callable[[tuple[str, str]], None]] = {}

    def App() -> object:
        pair, set_pair = use_state(("a", "b"))
        api["setPair"] = set_pair
        return create_element(Fragment, None, pair[0], pair[1])

    root = create_noop_root()
    root.render(create_element(App))
    assert root.container.last_committed == ["a", "b"]
    cast(Callable[[tuple[str, str]], None], api["setPair"])(("x", "y"))
    root.flush()
    assert root.container.last_committed == ["x", "y"]
