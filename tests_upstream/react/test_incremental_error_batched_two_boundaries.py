from __future__ import annotations

from ryact import Component, create_element
from ryact.concurrent import fragment
from ryact_testkit import create_noop_root


def test_two_error_boundaries_catch_independent_mount_errors() -> None:
    # Upstream: ReactIncrementalErrorHandling-test.internal.js
    # "catches render error in a boundary during batched mounting"
    class Bomb(Component):
        def render(self) -> object:
            raise RuntimeError("boom")

    class Boundary(Component):
        @classmethod
        def getDerivedStateFromError(cls, _err: BaseException) -> dict[str, object] | None:  # noqa: N802
            return {"hasError": True}

        def render(self) -> object:
            if bool(self.state.get("hasError")):
                return create_element("div", {"text": "ok"})
            return create_element(Bomb)

    root = create_noop_root()
    root.render(
        fragment(
            create_element(Boundary, {"key": "a"}),
            create_element(Boundary, {"key": "b"}),
        ),
    )
    snap = root.container.last_committed
    assert isinstance(snap, list)
    assert len(snap) == 2
    assert snap[0] == snap[1] == {
        "type": "div",
        "key": None,
        "props": {"text": "ok"},
        "children": [],
    }
