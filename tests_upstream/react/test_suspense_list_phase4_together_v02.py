from __future__ import annotations

from typing import Any

from ryact import create_element
from ryact.concurrent import Suspend, Thenable, fragment, suspense_list
from ryact_testkit import create_noop_root


def _span(value: str) -> Any:
    return create_element("span", {"text": value})


def _suspense(*, fallback: Any, child: Any, key: str) -> Any:
    return create_element("__suspense__", {"fallback": fallback, "children": (child,)}, key=key)


def test_displays_all_together() -> None:
    # Upstream: ReactSuspenseList-test.js — "displays all \"together\""
    t1, t2 = Thenable(), Thenable()
    s1, s2 = {"ready": False}, {"ready": False}

    def A() -> Any:
        if not s1["ready"]:
            raise Suspend(t1)
        return _span("A")

    def B() -> Any:
        if not s2["ready"]:
            raise Suspend(t2)
        return _span("B")

    root = create_noop_root()
    root.render(
        suspense_list(
            reveal_order="together",
            children=fragment(
                _suspense(fallback=_span("A..."), child=create_element(A), key="a"),
                _suspense(fallback=_span("B..."), child=create_element(B), key="b"),
            ),
        )
    )
    root.flush()
    snap = root.get_children_snapshot()
    assert isinstance(snap, list)
    assert [x["props"]["text"] for x in snap] == ["A...", "B..."]


def test_displays_all_together_during_an_update() -> None:
    # Upstream: ReactSuspenseList-test.js — "displays all \"together\" during an update"
    t1, t2 = Thenable(), Thenable()
    s1, s2 = {"ready": True}, {"ready": True}
    step = {"value": 0}

    def A() -> Any:
        if step["value"] == 1 and not s1["ready"]:
            raise Suspend(t1)
        return _span("A")

    def B() -> Any:
        if step["value"] == 1 and not s2["ready"]:
            raise Suspend(t2)
        return _span("B")

    root = create_noop_root()
    element = suspense_list(
        reveal_order="together",
        children=fragment(
            _suspense(fallback=_span("A..."), child=create_element(A), key="a"),
            _suspense(fallback=_span("B..."), child=create_element(B), key="b"),
        ),
    )
    root.render(element)
    root.flush()
    snap0 = root.get_children_snapshot()
    assert isinstance(snap0, list)
    assert [x["props"]["text"] for x in snap0] == ["A", "B"]

    # Update: both now suspend → together should show both fallbacks.
    s1["ready"] = False
    s2["ready"] = False
    step["value"] = 1
    root.render(element)
    root.flush()
    snap1 = root.get_children_snapshot()
    assert isinstance(snap1, list)
    assert [x["props"]["text"] for x in snap1] == ["A...", "B..."]

