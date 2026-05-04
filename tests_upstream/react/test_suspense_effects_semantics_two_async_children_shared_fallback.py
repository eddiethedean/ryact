from __future__ import annotations

from collections.abc import Callable
from typing import Any, cast

from ryact import create_element, use_state
from ryact.concurrent import Suspend, Thenable, suspense
from ryact_testkit import create_noop_root


def LeafA(**props: object) -> object:
    if not bool(props["ready"]):
        raise Suspend(cast(Thenable, props["t"]))
    return create_element("span", {"key": "ka", "text": "a"})


def LeafB(**props: object) -> object:
    if not bool(props["ready"]):
        raise Suspend(cast(Thenable, props["t"]))
    return create_element("span", {"key": "kb", "text": "b"})


def test_shared_fallback_when_two_children_suspend_then_both_resolve() -> None:
    # Upstream: ReactSuspenseEffectsSemantics-test.js
    # "should be only destroy layout effects once if a tree suspends in multiple places"
    # (snapshot slice: two independent suspending leaves under one boundary)
    ta, tb = Thenable(), Thenable()
    api: dict[str, Any] = {}

    def App() -> object:
        ready, set_ready = use_state(False)
        api["resolve"] = lambda: (ta.resolve(), tb.resolve(), set_ready(True))
        return suspense(
            fallback=create_element("div", {"text": "fb"}),
            children=create_element(
                "div",
                {"key": "wrap"},
                create_element(LeafA, {"key": "ca", "ready": ready, "t": ta}),
                create_element(LeafB, {"key": "cb", "ready": ready, "t": tb}),
            ),
        )

    root = create_noop_root()
    root.render(create_element(App))
    assert root.container.last_committed_as_dict() == {
        "type": "div",
        "key": None,
        "props": {"text": "fb"},
        "children": [],
    }
    cast(Callable[[], None], api["resolve"])()
    root.flush()
    snap = root.container.last_committed_as_dict()
    assert snap["type"] == "div"
    kids = snap["children"]
    assert len(kids) == 2
    assert kids[0]["props"]["text"] == "a"
    assert kids[1]["props"]["text"] == "b"
