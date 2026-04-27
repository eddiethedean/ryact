from __future__ import annotations

import pytest
from ryact import Component, create_element
from ryact_testkit import create_noop_root


def test_can_schedule_updates_after_uncaught_error_during_unmounting() -> None:
    # Upstream: ReactIncrementalErrorHandling-test.internal.js
    # "can schedule updates after uncaught error during unmounting"
    class Broken(Component):
        def render(self) -> object:
            return create_element("div")

        def componentWillUnmount(self) -> None:
            raise RuntimeError("Hello")

    class Foo(Component):
        def render(self) -> object:
            return None

    root = create_noop_root()
    root.render(create_element(Broken))
    assert root.container.last_committed == {
        "type": "div",
        "key": None,
        "props": {},
        "children": [],
    }
    with pytest.raises(RuntimeError, match="Hello"):
        root.render(create_element("div"))
    root.render(create_element(Foo))
    assert root.container.last_committed is None
