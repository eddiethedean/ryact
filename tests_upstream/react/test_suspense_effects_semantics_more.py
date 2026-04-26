from __future__ import annotations

from ryact import create_element
from ryact.concurrent import Suspend, Thenable, fragment, suspense
from ryact_testkit import create_noop_root


def test_multiple_sibling_suspense_boundaries_resolve_together() -> None:
    # Upstream: ReactSuspenseEffectsSemantics-test.js
    # "should show nested host nodes if multiple boundaries resolve at the same time"
    t1, t2 = Thenable(), Thenable()
    r1, r2 = {"ok": False}, {"ok": False}

    def A1() -> object:
        if not r1["ok"]:
            raise Suspend(t1)
        return create_element("span", {"text": "1"})

    def A2() -> object:
        if not r2["ok"]:
            raise Suspend(t2)
        return create_element("span", {"text": "2"})

    inner = fragment(
        suspense(fallback=create_element("div", {"text": "fb1"}), children=create_element(A1)),
        suspense(fallback=create_element("div", {"text": "fb2"}), children=create_element(A2)),
    )
    root = create_noop_root()
    root.render(
        suspense(fallback=create_element("div", {"text": "outer"}), children=inner),
    )
    assert root.container.last_committed == [
        {"type": "div", "key": None, "props": {"text": "fb1"}, "children": []},
        {"type": "div", "key": None, "props": {"text": "fb2"}, "children": []},
    ]
    r1["ok"] = True
    r2["ok"] = True
    t1.resolve()
    t2.resolve()
    root.flush()
    assert root.container.last_committed == [
        {"type": "span", "key": None, "props": {"text": "1"}, "children": []},
        {"type": "span", "key": None, "props": {"text": "2"}, "children": []},
    ]


def test_partial_reveal_one_suspense_child_while_sibling_still_fallback() -> None:
    # Upstream: ReactSuspenseEffectsSemantics-test.js
    # "should wait to reveal an inner child when inner one reveals first"
    t1, t2 = Thenable(), Thenable()
    r1, r2 = {"ok": False}, {"ok": False}

    def A1() -> object:
        if not r1["ok"]:
            raise Suspend(t1)
        return create_element("span", {"text": "1"})

    def A2() -> object:
        if not r2["ok"]:
            raise Suspend(t2)
        return create_element("span", {"text": "2"})

    inner = fragment(
        suspense(fallback=create_element("div", {"text": "fb1"}), children=create_element(A1)),
        suspense(fallback=create_element("div", {"text": "fb2"}), children=create_element(A2)),
    )
    root = create_noop_root()
    root.render(
        suspense(fallback=create_element("div", {"text": "outer"}), children=inner),
    )
    r1["ok"] = True
    t1.resolve()
    root.flush()
    assert root.container.last_committed == [
        {"type": "span", "key": None, "props": {"text": "1"}, "children": []},
        {"type": "div", "key": None, "props": {"text": "fb2"}, "children": []},
    ]
