from __future__ import annotations

from ryact import create_element
from ryact.concurrent import fragment
from ryact_testkit import create_noop_root


def test_fragment_renders_zero_children_via_noop() -> None:
    # Upstream: ReactFragment-test.js — "should render zero children via noop renderer"
    root = create_noop_root()
    root.render(fragment())
    assert root.container.last_committed == []


def test_fragment_renders_single_child_via_noop() -> None:
    # Upstream: ReactFragment-test.js — "should render a single child via noop renderer"
    root = create_noop_root()
    root.render(fragment(create_element("span", {"text": "x"})))
    committed = root.container.last_committed
    assert isinstance(committed, list)
    assert len(committed) == 1
    assert committed[0]["type"] == "span"


def test_fragment_renders_multiple_children_via_noop() -> None:
    # Upstream: ReactFragment-test.js — "should render multiple children via noop renderer"
    root = create_noop_root()
    root.render(
        fragment(
            create_element("span", {"text": "a"}),
            create_element("span", {"text": "b"}),
        )
    )
    committed = root.container.last_committed
    assert isinstance(committed, list)
    assert [c["props"]["text"] for c in committed] == ["a", "b"]


def test_fragment_renders_iterable_spread_children_via_noop() -> None:
    # Upstream: ReactFragment-test.js — "should render an iterable via noop renderer"
    # Python equivalent: spread a list/tuple into fragment(...).
    root = create_noop_root()
    nodes = [create_element("i", {"text": str(i)}) for i in range(2)]
    root.render(fragment(*nodes))
    committed = root.container.last_committed
    assert isinstance(committed, list)
    assert [c["props"]["text"] for c in committed] == ["0", "1"]
