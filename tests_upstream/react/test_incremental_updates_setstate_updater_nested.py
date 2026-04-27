from __future__ import annotations

from ryact import Component, create_element
from ryact_testkit import create_noop_root


def test_updates_triggered_from_inside_a_class_setstate_updater() -> None:
    # Upstream: ReactIncrementalUpdates-test.js — "updates triggered from inside a class setState updater"
    commits: list[int] = []

    class App(Component):
        def componentDidMount(self) -> None:
            def updater(prev_state: object, props: object) -> object:
                # schedule another update from inside updater
                self.set_state({"n": 2})
                return {"n": 1}

            self.set_state(updater)  # type: ignore[arg-type]

        def render(self) -> object:
            n = int(self.state.get("n", 0))
            commits.append(n)
            return create_element("div", {"text": str(n)})

    root = create_noop_root()
    root.render(create_element(App))
    assert root.get_children_snapshot()["props"]["text"] == "0"

    # first flush applies updater -> n=1, enqueues nested n=2 for later
    root.flush()
    assert root.get_children_snapshot()["props"]["text"] == "1"

    # second flush applies nested update
    root.flush()
    assert root.get_children_snapshot()["props"]["text"] == "2"

    assert commits == [0, 1, 2]

