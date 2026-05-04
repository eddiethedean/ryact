from __future__ import annotations

from ryact import Component, create_element
from ryact_testkit import create_noop_root


def test_calls_setstate_callback_even_if_component_bails_out() -> None:
    # Upstream: ReactIncrementalSideEffects-test.js — "calls setState callback even if component bails out"
    log: list[str] = []
    renders: list[int] = []

    class App(Component):
        def shouldComponentUpdate(self, next_props: object, next_state: object) -> bool:  # noqa: N802
            return False

        def componentDidMount(self) -> None:
            self.set_state({"n": 1}, callback=lambda: log.append("cb"))

        def render(self) -> object:
            renders.append(1)
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
    # bails out: no re-render, host tree unchanged, but callback still fires.
    assert root.container.last_committed == {
        "type": "div",
        "key": None,
        "props": {"text": "0"},
        "children": [],
    }
    assert log == ["cb"]
    assert len(renders) == 1
