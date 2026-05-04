from __future__ import annotations

import pytest
from ryact import Component, create_element
from ryact_testkit import create_noop_root


def test_handles_error_thrown_by_top_level_callback() -> None:
    # Upstream: ReactIncrementalErrorHandling-test.internal.js
    # "handles error thrown by top-level callback"
    root = create_noop_root()

    def boom() -> None:
        raise RuntimeError("Error!")

    with pytest.raises(RuntimeError, match="Error!"):
        root.render(create_element("div"), callback=boom)


def test_calls_correct_lifecycles_after_catching_error_mixed() -> None:
    # Upstream: ReactIncrementalErrorHandling-test.internal.js
    # "calls the correct lifecycles on the error boundary after catching an error (mixed)"
    log: list[str] = []

    def BadRender(**_props: object) -> object:
        log.append("throw")
        raise RuntimeError("oops!")

    class Parent(Component):
        def componentDidCatch(self, _err: BaseException) -> None:  # noqa: N802
            log.append("did catch")
            self.set_state({"error": True})

        def componentDidUpdate(self) -> None:  # noqa: N802
            log.append("did update")

        def render(self) -> object:
            if bool(self.state.get("error")):
                log.append("render error message")
                return create_element("div", {"text": "error"})
            log.append("render")
            return create_element(BadRender)

    root = create_noop_root()
    root.render(create_element(Parent))
    assert log == [
        "render",
        "throw",
        "render",
        "throw",
        "did catch",
        "render error message",
        "did update",
    ]
    assert root.container.last_committed == {
        "type": "div",
        "key": None,
        "props": {"text": "error"},
        "children": [],
    }
