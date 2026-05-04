from __future__ import annotations

from collections.abc import Callable

from ryact import Component, create_element, use_state
from ryact_testkit import create_noop_root


def test_catches_reconciler_errors_in_a_boundary_during_update() -> None:
    # Upstream: ReactIncrementalErrorHandling-test.internal.js
    # "catches reconciler errors in a boundary during update"
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

        def render(self) -> object:
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
    api["setBoom"](True)
    root.flush()
    assert root.container.last_committed == {
        "type": "div",
        "key": None,
        "props": {"text": "err"},
        "children": [],
    }
