from __future__ import annotations

from typing import Any, cast

from ryact import Component, create_element
from ryact_testkit import create_noop_root


def test_base_state_of_update_queue_is_initialized_to_memoized_state() -> None:
    # Upstream: ReactIncrementalUpdates-test.js —
    # "base state of update queue is initialized to its fiber's memoized state"
    seen: list[int] = []

    class App(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            # Establish an initial memoized state.
            self._state["n"] = 0  # type: ignore[attr-defined]

        def componentDidMount(self) -> None:  # noqa: N802
            def updater(prev_state: object, _props: object) -> object:
                n = int(cast(Any, getattr(prev_state, "get", lambda k, d=None: d)("n", -1)))
                seen.append(n)
                return {"n": n + 1}

            self.set_state(updater)  # type: ignore[arg-type]

        def render(self) -> object:
            return create_element("div", {"text": str(self.state.get("n", "?"))})

    root = create_noop_root()
    root.render(create_element(App))
    # Flush update scheduled by cDM.
    root.flush()

    assert seen == [0]
    assert root.get_children_snapshot()["props"]["text"] == "1"
