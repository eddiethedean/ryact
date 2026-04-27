from __future__ import annotations

from ryact import Component, create_element
from ryact.concurrent import start_transition
from ryact_testkit import create_noop_root


def test_replacestate_replaces_state_instead_of_merging() -> None:
    # Upstream: ReactIncrementalUpdates-test.js (replaceState semantics)
    class App(Component):
        def componentDidMount(self) -> None:
            self.set_state({"a": 1, "b": 2})
            # replaceState drops equal-or-lower priority updates; run at a lower
            # priority so the previous default-priority setState is preserved.
            start_transition(lambda: self.replace_state({"a": 3}))

        def render(self) -> object:
            a = self.state.get("a")
            b = self.state.get("b")
            return create_element("div", {"text": f"a={a},b={b}"})

    root = create_noop_root()
    root.render(create_element(App))
    assert root.get_children_snapshot()["props"]["text"] == "a=None,b=None"

    root.flush()
    # replaceState should drop keys not present in next state.
    assert root.get_children_snapshot()["props"]["text"] == "a=3,b=None"
    assert [c["props"]["text"] for c in root.container.commits if c is not None] == [
        "a=None,b=None",
        "a=1,b=2",
        "a=3,b=None",
    ]

