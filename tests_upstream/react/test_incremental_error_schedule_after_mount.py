from __future__ import annotations

from ryact import Component, create_element
from ryact_testkit import create_noop_root


def test_can_schedule_updates_after_error_in_render_on_mount() -> None:
    # Upstream: ReactIncrementalErrorHandling-test.internal.js
    # "can schedule updates after uncaught error in render on mount"
    class Child(Component):
        def render(self) -> object:
            raise RuntimeError("boom")

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
            return create_element(Child)

    root = create_noop_root()
    root.render(create_element(Boundary))
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
