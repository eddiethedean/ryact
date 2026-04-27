from __future__ import annotations

from ryact import create_element
from ryact.concurrent import Suspend, Thenable, suspense
from ryact_testkit import create_noop_root


def test_suspense_async_nested_below_host_div_shows_fallback() -> None:
    # Upstream: ReactSuspenseEffectsSemantics-test.js
    # "should be destroyed and recreated when nested below host components"
    t = Thenable()
    ok = {"v": False}

    def AsyncChild() -> object:
        if not ok["v"]:
            raise Suspend(t)
        return create_element("span", {"text": "done"})

    root = create_noop_root()
    root.render(
        create_element(
            "div",
            None,
            suspense(
                fallback=create_element("div", {"text": "fb"}),
                children=create_element(AsyncChild),
            ),
        ),
    )
    snap = root.container.last_committed
    assert isinstance(snap, dict)
    assert snap["type"] == "div"
    assert len(snap["children"]) == 1
    inner = snap["children"][0]
    assert inner == {"type": "div", "key": None, "props": {"text": "fb"}, "children": []}
    ok["v"] = True
    t.resolve()
    root.flush()
    snap2 = root.container.last_committed
    assert snap2["type"] == "div"
    assert snap2["children"][0] == {
        "type": "span",
        "key": None,
        "props": {"text": "done"},
        "children": [],
    }


def test_suspense_fallback_nested_deeply_when_inner_tree_suspends() -> None:
    # Upstream: ReactSuspenseEffectsSemantics-test.js
    # "should be cleaned up deeper inside of a subtree that suspends"
    t = Thenable()
    ok = {"v": False}

    def AsyncChild() -> object:
        if not ok["v"]:
            raise Suspend(t)
        return create_element("span", {"text": "leaf"})

    inner = suspense(
        fallback=create_element("div", {"text": "inner_fb"}),
        children=create_element(AsyncChild),
    )
    root = create_noop_root()
    root.render(
        suspense(
            fallback=create_element("div", {"text": "outer_fb"}),
            children=create_element("div", None, inner),
        ),
    )
    snap = root.container.last_committed
    assert snap["type"] == "div"
    assert snap["children"][0]["props"]["text"] == "inner_fb"
    ok["v"] = True
    t.resolve()
    root.flush()
    out = root.container.last_committed
    assert out["type"] == "div"
    assert len(out["children"]) == 1
    assert out["children"][0] == {
        "type": "span",
        "key": None,
        "props": {"text": "leaf"},
        "children": [],
    }
