from __future__ import annotations

from ryact import Component, create_element
from ryact_testkit import create_noop_root


def test_render_phase_set_state_then_error_finishes_without_spinning() -> None:
    # Upstream: ReactIncrementalErrorHandling-test.internal.js
    # "does not infinite loop if there's a render phase update in the same render as an error"
    class Child(Component):
        def render(self) -> object:
            if not bool(self.state.get("touched")):
                self.set_state({"touched": True})
            raise RuntimeError("boom")

    class Boundary(Component):
        @classmethod
        def getDerivedStateFromError(cls, _err: BaseException) -> dict[str, object] | None:  # noqa: N802
            return {"hasError": True}

        def render(self) -> object:
            if bool(self.state.get("hasError")):
                return create_element("div", {"text": "fb"})
            return create_element(Child)

    root = create_noop_root()
    root.render(create_element(Boundary))
    assert root.container.last_committed == {
        "type": "div",
        "key": None,
        "props": {"text": "fb"},
        "children": [],
    }
