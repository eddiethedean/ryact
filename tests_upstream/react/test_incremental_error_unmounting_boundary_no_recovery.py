from __future__ import annotations

import pytest
from ryact import Component, create_element
from ryact_testkit import create_noop_root


def test_should_not_attempt_to_recover_an_unmounting_error_boundary() -> None:
    # Upstream: ReactIncrementalErrorHandling-test.internal.js
    # "should not attempt to recover an unmounting error boundary"
    log: list[str] = []

    class Parent(Component):
        def componentWillUnmount(self) -> None:
            log.append("Parent componentWillUnmount")

        def render(self) -> object:
            return create_element(Boundary)

    class Boundary(Component):
        def componentDidCatch(self, _err: BaseException) -> None:
            log.append("componentDidCatch")

        def render(self) -> object:
            return create_element(ThrowsOnUnmount)

    class ThrowsOnUnmount(Component):
        def componentWillUnmount(self) -> None:
            log.append("ThrowsOnUnmount componentWillUnmount")
            raise RuntimeError("unmount error")

        def render(self) -> object:
            return None

    root = create_noop_root()
    root.render(create_element(Parent))
    log.clear()
    with pytest.raises(RuntimeError, match="unmount error"):
        root.render(None)
    assert log == [
        "Parent componentWillUnmount",
        "ThrowsOnUnmount componentWillUnmount",
    ]
    assert "componentDidCatch" not in log

    # Upstream ends by re-mounting the tree; snapshot may be null when the subtree is empty.
    root.render(create_element(Parent))
    assert len(root.container.commits) == 3
