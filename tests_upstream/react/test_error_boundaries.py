from __future__ import annotations

from ryact import Component, create_element
from ryact_testkit import create_noop_root


def test_getderivedstatefromerror_can_recover_by_rendering_an_element_of_the_same_type() -> None:
    # Upstream: ErrorBoundaryReconciliation-test.internal.js
    # "getDerivedStateFromError can recover by rendering an element of the same type"
    root = create_noop_root()
    log: list[str] = []

    class Bomb(Component):
        def render(self) -> object:
            raise RuntimeError("boom")

    class Boundary(Component):
        __slots__ = ()  # state lives on base Component

        @classmethod
        def getDerivedStateFromError(cls, _err: BaseException) -> dict[str, object] | None:  # noqa: N802
            return {"hasError": True}

        def componentDidCatch(self, _err: BaseException) -> None:  # noqa: N802
            log.append("didCatch")

        def render(self) -> object:
            if bool(self.state.get("hasError")):
                return create_element("div", {"status": "recovered"})
            return create_element("div", None, create_element(Bomb))

    root.render(create_element(Boundary))
    committed = root.container.last_committed
    assert committed is not None
    assert committed["type"] == "div"
    assert committed["props"]["status"] == "recovered"
    assert "didCatch" in log
