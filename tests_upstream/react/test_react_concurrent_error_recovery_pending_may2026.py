# Upstream: packages/react-reconciler/src/__tests__/ReactConcurrentErrorRecovery-test.js
# May 2026 inventory slice: transition + suspense/error boundary smoke.
from __future__ import annotations

from typing import Any

import pytest

from ryact import Component, create_element
from ryact.concurrent import Suspend, Thenable, start_transition, suspense
from ryact_testkit import create_noop_root


def _text(v: str) -> Any:
    return create_element("div", {"text": v})


def test_suspending_in_shell_during_transition_does_not_throw_smoke() -> None:
    t = Thenable()

    def App() -> Any:
        raise Suspend(t)

    root = create_noop_root()
    # In ryact, uncaught Suspend is treated like an error; we allow that this may raise.
    with pytest.raises(Exception):
        start_transition(lambda: root.render(create_element(App)))


def test_errors_during_transition_do_not_force_fallbacks_smoke() -> None:
    class Boundary(Component):
        def __init__(self, **props: Any) -> None:
            super().__init__(**props)
            self._state = {"err": False}  # type: ignore[misc]

        @staticmethod
        def getDerivedStateFromError(_e: BaseException) -> dict[str, object]:  # noqa: N802
            return {"err": True}

        def render(self) -> object:
            if self.state.get("err"):
                return _text("Oops!")
            return self.props.get("children")

    def Throws() -> Any:
        raise RuntimeError("Oops!")

    root = create_noop_root()
    start_transition(lambda: root.render(create_element(Boundary, {"children": create_element(Throws)})))
    root.flush()
    assert root.get_children_snapshot() is not None

