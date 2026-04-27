from __future__ import annotations

from ryact import Component, create_element
from ryact_testkit import create_noop_root


def test_component_did_catch_receives_error_with_component_stack_annotation() -> None:
    # Upstream: ReactIncrementalErrorHandling-test.internal.js
    # "provides component stack to the error boundary with componentDidCatch"
    caught: list[BaseException] = []

    class Bomb(Component):
        def render(self) -> object:
            raise RuntimeError("boom")

    class Boundary(Component):
        @classmethod
        def getDerivedStateFromError(cls, _err: BaseException) -> dict[str, object] | None:  # noqa: N802
            return {"hasError": True}

        def componentDidCatch(self, err: BaseException) -> None:  # noqa: N802
            caught.append(err)

        def render(self) -> object:
            if bool(self.state.get("hasError")):
                return create_element("div", {"text": "fb"})
            return create_element(Bomb)

    root = create_noop_root()
    root.render(create_element(Boundary))
    assert root.container.last_committed == {
        "type": "div",
        "key": None,
        "props": {"text": "fb"},
        "children": [],
    }
    root.flush()
    assert len(caught) == 1
    assert "Component stack:" in str(caught[0])
