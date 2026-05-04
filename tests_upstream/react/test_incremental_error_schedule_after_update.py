from __future__ import annotations

from collections.abc import Callable
from typing import cast

from ryact import Component, create_element, use_state
from ryact_testkit import create_noop_root


def test_can_schedule_updates_after_error_in_render_on_update() -> None:
    # Upstream: ReactIncrementalErrorHandling-test.internal.js
    # "can schedule updates after uncaught error in render on update"
    api: dict[str, Callable[[bool], None]] = {}

    class Child(Component):
        def render(self) -> object:
            if bool(self.props.get("boom")):
                raise RuntimeError("boom")
            return create_element("span", {"text": "ok"})

    class Boundary(Component):
        @classmethod
        def getDerivedStateFromError(cls, _err: BaseException) -> dict[str, object] | None:  # noqa: N802
            return {"hasError": True}

        def componentDidCatch(self, _err: BaseException) -> None:  # noqa: N802
            self.set_state({"after": True})

        def render(self) -> object:
            if bool(self.state.get("after")):
                return create_element("div", {"text": "after"})
            if bool(self.state.get("hasError")):
                return create_element("div", {"text": "err"})
            return create_element(Child, {"boom": bool(self.props.get("boom"))})

    def App() -> object:
        boom, set_boom = use_state(False)
        api["setBoom"] = set_boom
        return create_element(Boundary, {"boom": boom})

    root = create_noop_root()
    root.render(create_element(App))
    assert root.container.last_committed == {
        "type": "span",
        "key": None,
        "props": {"text": "ok"},
        "children": [],
    }
    cast(Callable[[bool], None], api["setBoom"])(True)
    root.flush()
    assert root.container.last_committed == {
        "type": "div",
        "key": None,
        "props": {"text": "err"},
        "children": [],
    }
    root.flush()
    assert root.container.last_committed == {
        "type": "div",
        "key": None,
        "props": {"text": "after"},
        "children": [],
    }
