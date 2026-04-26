from __future__ import annotations

from ryact import Component, create_element
from ryact_testkit import create_noop_root


def test_catches_render_error_in_boundary_during_synchronous_mount() -> None:
    # Upstream: ReactIncrementalErrorHandling-test.internal.js
    # "catches render error in a boundary during synchronous mounting"
    log: list[str] = []

    class Bomb(Component):
        def render(self) -> object:
            raise RuntimeError("boom")

    class Boundary(Component):
        @classmethod
        def getDerivedStateFromError(cls, _err: BaseException) -> dict[str, object] | None:  # noqa: N802
            return {"hasError": True}

        def componentDidCatch(self, _err: BaseException) -> None:  # noqa: N802
            log.append("didCatch")

        def render(self) -> object:
            if bool(self.state.get("hasError")):
                return create_element("div", {"text": "fallback"})
            return create_element(Bomb)

    root = create_noop_root()
    root.render(create_element(Boundary))
    snap = root.container.last_committed
    assert snap is not None
    assert snap["props"]["text"] == "fallback"
    assert "didCatch" in log
