from __future__ import annotations

from ryact import Component, create_element
from ryact_testkit import create_noop_root


def test_componentdidcatch_can_recover_by_rendering_an_element_of_a_different_type() -> None:
    # Upstream: ErrorBoundaryReconciliation-test.internal.js
    # "componentDidCatch can recover by rendering an element of a different type"
    class Bomb(Component):
        def render(self) -> object:
            raise RuntimeError("boom")

    class Boundary(Component):
        @classmethod
        def getDerivedStateFromError(cls, _err: BaseException) -> dict[str, object] | None:  # noqa: N802
            return {"hasError": True}

        def componentDidCatch(self, _err: BaseException) -> None:  # noqa: N802
            return

        def render(self) -> object:
            if bool(self.state.get("hasError")):
                return create_element("span", {"text": "recovered"})
            return create_element("div", None, create_element(Bomb))

    root = create_noop_root()
    root.render(create_element(Boundary))
    committed = root.container.last_committed
    assert committed is not None
    assert committed["type"] == "span"
    assert committed["props"]["text"] == "recovered"
