from __future__ import annotations

from collections.abc import Callable

from ryact import create_element
from ryact.concurrent import Suspend, Thenable, suspense


def _initial_suspend_then_resolve() -> tuple[Thenable, dict[str, bool], Callable[[], object]]:
    t = Thenable()
    ok = {"v": False}

    def AsyncChild() -> object:
        if not ok["v"]:
            raise Suspend(t)
        return create_element("span", {"text": "done"})

    return t, ok, AsyncChild


def test_initial_mount_suspend_sync_noop_matches_upstream_snapshot() -> None:
    # Upstream: ReactSuspenseEffectsSemantics-test.js — when a component suspends during
    # initial mount / "should not change behavior in sync"
    from ryact_testkit import create_noop_root

    t, ok, AsyncChild = _initial_suspend_then_resolve()
    root = create_noop_root()
    root.render(
        suspense(
            fallback=create_element("div", {"text": "fb"}),
            children=create_element(AsyncChild),
        ),
    )
    assert root.container.last_committed_as_dict() == {
        "type": "div",
        "key": None,
        "props": {"text": "fb"},
        "children": [],
    }
    ok["v"] = True
    t.resolve()
    root.flush()
    assert root.container.last_committed_as_dict() == {
        "type": "span",
        "key": None,
        "props": {"text": "done"},
        "children": [],
    }


def test_initial_mount_suspend_concurrent_noop_matches_upstream_snapshot() -> None:
    # Upstream: ReactSuspenseEffectsSemantics-test.js — same describe /
    # "should not change behavior in concurrent mode" (noop host has a single schedule path).
    from ryact_testkit import create_noop_root

    t, ok, AsyncChild = _initial_suspend_then_resolve()
    root = create_noop_root()
    root.render(
        suspense(
            fallback=create_element("div", {"text": "fb"}),
            children=create_element(AsyncChild),
        ),
    )
    assert root.container.last_committed_as_dict()["props"]["text"] == "fb"
    ok["v"] = True
    t.resolve()
    root.flush()
    assert root.container.last_committed_as_dict()["props"]["text"] == "done"
