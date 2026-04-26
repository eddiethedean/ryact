from __future__ import annotations

from ryact import Component, create_element
from ryact_testkit import create_noop_root


def test_calls_callback_after_update_is_flushed() -> None:
    # Upstream: ReactIncrementalSideEffects-test.js — "calls callback after update is flushed"
    log: list[str] = []

    class App(Component):
        def componentDidMount(self) -> None:
            self.set_state({"n": 1}, callback=lambda: log.append("cb"))

        def render(self) -> object:
            n = self.state.get("n", 0)
            return create_element("div", {"text": str(n)})

    root = create_noop_root()
    root.render(create_element(App))
    assert root.container.last_committed == {
        "type": "div",
        "key": None,
        "props": {"text": "0"},
        "children": [],
    }
    root.flush()
    assert root.container.last_committed == {
        "type": "div",
        "key": None,
        "props": {"text": "1"},
        "children": [],
    }
    assert log == ["cb"]
