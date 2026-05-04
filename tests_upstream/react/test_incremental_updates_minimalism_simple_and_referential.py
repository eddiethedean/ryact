from __future__ import annotations

from ryact import create_element
from ryact_testkit import create_noop_root


def test_minimalism_should_render_a_simple_component() -> None:
    # Upstream: ReactIncrementalUpdatesMinimalism-test.js — "should render a simple component"
    root = create_noop_root()
    root.render(create_element("div", {"text": "hi"}))
    assert root.get_children_snapshot() == {
        "type": "div",
        "key": None,
        "props": {"text": "hi"},
        "children": [],
    }


def test_minimalism_should_not_diff_referentially_equal_host_elements() -> None:
    # Upstream: ReactIncrementalUpdatesMinimalism-test.js — "should not diff referentially equal host elements"
    root = create_noop_root()
    el = create_element("div", {"text": "same"})

    root.render(el)
    root.clear_ops()

    # Rendering the exact same element object should not produce host mutations.
    root.render(el)
    assert root.get_ops() == []
