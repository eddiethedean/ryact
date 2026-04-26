from __future__ import annotations

from ryact import create_element
from ryact_testkit import create_noop_root


def test_should_render_a_simple_host_element() -> None:
    # Upstream: ReactIncremental-test.js — "should render a simple component"
    # (minimal host-tree slice on the noop renderer harness).
    root = create_noop_root()
    root.render(create_element("div", {"id": "hello"}))
    assert root.container.last_committed == {
        "type": "div",
        "key": None,
        "props": {"id": "hello"},
        "children": [],
    }
