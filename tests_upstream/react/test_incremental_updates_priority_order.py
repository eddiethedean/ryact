from __future__ import annotations

from ryact import Component, create_element
from ryact.concurrent import start_transition
from ryact_testkit import create_noop_root


def test_applies_updates_in_order_of_priority() -> None:
    # Upstream: ReactIncrementalUpdates-test.js — "applies updates in order of priority"
    commits: list[str] = []

    class App(Component):
        def componentDidMount(self) -> None:
            start_transition(lambda: self.set_state({"step": "transition"}))
            self.set_state({"step": "sync"})

        def render(self) -> object:
            step = self.state.get("step", "initial")
            commits.append(step)
            return create_element("div", {"text": step})

    root = create_noop_root()
    root.render(create_element(App))
    root.flush()

    # Expect sync update to commit before transition update.
    assert commits[:1] == ["initial"]
    assert "sync" in commits
    assert "transition" in commits
    assert commits.index("sync") < commits.index("transition")

