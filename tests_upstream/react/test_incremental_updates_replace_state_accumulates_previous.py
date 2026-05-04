from __future__ import annotations

from typing import Any, cast

from ryact import Component, create_element
from ryact.concurrent import start_transition
from ryact_testkit import create_noop_root


def test_replacestate_updater_sees_accumulation_of_previous_updates() -> None:
    # Upstream: ReactIncrementalUpdates-test.js —
    # "passes accumulation of previous updates to replaceState updater function"
    class App(Component):
        def componentDidMount(self) -> None:
            # First update merges in a=1
            self.set_state({"a": 1})

            # Then replaceState updater should observe the updated state.
            def repl(prev_state: object, props: object) -> object:
                a = int(cast(Any, getattr(prev_state, "get", lambda k, d=None: d)("a", 0)))
                return {"a": a + 1, "b": 2}

            # replaceState drops equal-or-lower priority updates; run it at a lower
            # priority so it does not drop the previous default-priority setState.
            start_transition(lambda: self.replace_state(repl))  # type: ignore[arg-type]

        def render(self) -> object:
            a = int(self.state.get("a", 0))
            b = int(self.state.get("b", 0))
            return create_element("div", {"text": f"{a},{b}"})

    root = create_noop_root()
    root.render(create_element(App))
    assert root.get_children_snapshot()["props"]["text"] == "0,0"

    root.flush()
    assert root.get_children_snapshot()["props"]["text"] == "2,2"
    assert [c["props"]["text"] for c in root.container.commits if c is not None] == [
        "0,0",
        "1,0",
        "2,2",
    ]
