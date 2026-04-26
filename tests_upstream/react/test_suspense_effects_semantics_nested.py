from __future__ import annotations

from ryact import create_element
from ryact.concurrent import Suspend, Thenable, suspense
from ryact_testkit import create_noop_root


def test_nested_suspense_inner_fallback_not_outer() -> None:
    # Upstream: ReactSuspenseEffectsSemantics-test.js — "should respect nested suspense boundaries"
    t = Thenable()
    ok = {"v": False}

    def InnerAsync() -> object:
        if not ok["v"]:
            raise Suspend(t)
        return create_element("span", {"text": "done"})

    inner = suspense(
        fallback=create_element("div", {"text": "inner_fb"}),
        children=create_element(InnerAsync),
    )
    outer = suspense(
        fallback=create_element("div", {"text": "outer_fb"}),
        children=inner,
    )
    root = create_noop_root()
    root.render(outer)
    assert root.container.last_committed == {
        "type": "div",
        "key": None,
        "props": {"text": "inner_fb"},
        "children": [],
    }
    ok["v"] = True
    t.resolve()
    root.flush()
    assert root.container.last_committed == {
        "type": "span",
        "key": None,
        "props": {"text": "done"},
        "children": [],
    }
