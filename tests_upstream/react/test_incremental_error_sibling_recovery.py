from __future__ import annotations

from ryact import Component, create_element
from ryact_testkit import create_noop_root


def test_continues_working_on_siblings_outside_error_subtree() -> None:
    # Upstream: ReactIncrementalErrorHandling-test.internal.js
    # "continues working on siblings of a component that throws"
    class Bad(Component):
        def render(self) -> object:
            raise RuntimeError("boom")

    class Boundary(Component):
        @classmethod
        def getDerivedStateFromError(cls, _err: BaseException) -> dict[str, object] | None:  # noqa: N802
            return {"hasError": True}

        def render(self) -> object:
            if bool(self.state.get("hasError")):
                return create_element("span", {"text": "recovered"})
            return create_element(Bad)

    class Wrapper(Component):
        def render(self) -> object:
            return create_element(
                "div",
                None,
                create_element(Boundary),
                create_element("span", {"text": "sibling"}),
            )

    root = create_noop_root()
    root.render(create_element(Wrapper))
    snap = root.container.last_committed
    assert snap is not None
    assert snap["type"] == "div"
    children = snap["children"]
    assert len(children) == 2
    assert children[0]["props"]["text"] == "recovered"
    assert children[1]["props"]["text"] == "sibling"
