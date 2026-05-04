from __future__ import annotations

from ryact import Component, create_element
from ryact.concurrent import start_transition
from ryact_testkit import create_noop_root


def test_applies_updates_with_equal_priority_in_insertion_order() -> None:
    # Upstream: ReactIncrementalUpdates-test.js — "applies updates with equal priority in insertion order"
    commits: list[str] = []

    class App(Component):
        def componentDidMount(self) -> None:
            def batch() -> None:
                start_transition(lambda: self.set_state({"step": "t1"}))
                start_transition(lambda: self.set_state({"step": "t2"}))

            root.batched_updates(batch)

        def render(self) -> object:
            step = self.state.get("step", "initial")
            commits.append(step)
            return create_element("div", {"text": step})

    root = create_noop_root()
    root.render(create_element(App))
    # Batched updates should not flush until we explicitly flush.
    assert root.get_children_snapshot()["props"]["text"] == "initial"

    root.flush()
    # Two equal-priority (transition) updates should apply in insertion order.
    assert "t1" in commits
    assert "t2" in commits
    assert commits.index("t1") < commits.index("t2")
