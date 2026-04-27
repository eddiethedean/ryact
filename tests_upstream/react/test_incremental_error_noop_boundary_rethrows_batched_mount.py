from __future__ import annotations

import pytest
from ryact import Component, create_element
from ryact_testkit import create_noop_root


def test_propagates_error_from_noop_error_boundary_during_batched_mounting() -> None:
    # Upstream: ReactIncrementalErrorHandling-test.internal.js
    # "propagates an error from a noop error boundary during batched mounting"
    log: list[str] = []

    class RethrowErrorBoundary(Component):
        def componentDidCatch(self, err: BaseException) -> None:  # noqa: N802
            log.append("RethrowErrorBoundary componentDidCatch")
            raise err

        def render(self) -> object:
            log.append("RethrowErrorBoundary render")
            ch = self.props.get("children") or ()
            return ch[0] if ch else None

    class BrokenRender(Component):
        def render(self) -> object:
            log.append("BrokenRender")
            raise RuntimeError("Hello")

    root = create_noop_root()
    root.render(
        create_element(RethrowErrorBoundary, None, create_element("span", {"text": "before"})),
    )
    log.clear()
    with pytest.raises(RuntimeError, match="Hello"):
        root.render(
            create_element(RethrowErrorBoundary, None, create_element(BrokenRender)),
        )
    assert log == [
        "RethrowErrorBoundary render",
        "BrokenRender",
        "RethrowErrorBoundary render",
        "BrokenRender",
        "RethrowErrorBoundary componentDidCatch",
    ]
    # Failed update does not commit a new snapshot; previous host tree remains.
    assert root.container.last_committed == {
        "type": "span",
        "key": None,
        "props": {"text": "before"},
        "children": [],
    }
