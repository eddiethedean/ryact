from __future__ import annotations

from ryact import Component, create_element
from ryact.concurrent import start_transition
from ryact_testkit import create_noop_root


def test_replacestate_drops_updates_with_equal_or_lesser_priority() -> None:
    # Upstream: ReactIncrementalUpdates-test.js —
    # "only drops updates with equal or lesser priority when replaceState is called"
    commits: list[str] = []

    class App(Component):
        def componentDidMount(self) -> None:
            def batch() -> None:
                start_transition(lambda: self.set_state({"step": "transition"}))
                self.replace_state({"step": "replace"})

            root.batched_updates(batch)

        def render(self) -> object:
            step = str(self.state.get("step", "initial"))
            commits.append(step)
            return create_element("div", {"text": step})

    root = create_noop_root()
    root.render(create_element(App))
    assert root.get_children_snapshot()["props"]["text"] == "initial"

    root.flush()
    # Transition update should be dropped; only replaceState remains.
    assert root.get_children_snapshot()["props"]["text"] == "replace"
    assert "transition" not in commits
