from __future__ import annotations

from typing import Any

from ryact import create_element
from ryact.concurrent import Suspend, Thenable, suspense
from ryact_testkit import create_noop_root


def _text(value: str) -> Any:
    return create_element("span", {"text": value})


def test_can_rerender_after_resolving_a_promise() -> None:
    # Upstream: ReactSuspenseWithNoopRenderer-test.js
    # "can rerender after resolving a promise"
    t = Thenable()
    state = {"ready": False}

    def AsyncText(*, value: str) -> Any:
        if not state["ready"]:
            raise Suspend(t)
        return _text(value)

    root = create_noop_root()
    root.render(
        suspense(
            fallback=create_element("div", {"text": "Loading"}),
            children=create_element(AsyncText, {"value": "A"}),
        )
    )
    root.flush()
    assert root.get_children_snapshot() == {
        "type": "div",
        "key": None,
        "props": {"text": "Loading"},
        "children": [],
    }

    state["ready"] = True
    t.resolve()
    root.flush()
    assert root.get_children_snapshot()["props"]["text"] == "A"


def test_after_showing_fallback_does_not_flip_back_until_update_finishes() -> None:
    # Upstream: ReactSuspenseWithNoopRenderer-test.js
    # "after showing fallback, should not flip back to primary content until the update that suspended finishes"
    t = Thenable()
    state = {"ready": True}

    def AsyncText(*, value: str) -> Any:
        if not state["ready"]:
            raise Suspend(t)
        return _text(value)

    root = create_noop_root()
    root.render(
        suspense(
            fallback=create_element("div", {"text": "Loading"}),
            children=create_element(AsyncText, {"value": "A"}),
        )
    )
    root.flush()
    assert root.get_children_snapshot()["props"]["text"] == "A"

    # Start an update that suspends.
    state["ready"] = False
    root.render(
        suspense(
            fallback=create_element("div", {"text": "Loading"}),
            children=create_element(AsyncText, {"value": "B"}),
        )
    )
    root.flush()
    assert root.get_children_snapshot()["props"]["text"] == "Loading"

    # Extra flushes must not revert to previously committed primary content.
    root.flush()
    assert root.get_children_snapshot()["props"]["text"] == "Loading"

    # Finish the suspended update.
    state["ready"] = True
    t.resolve()
    root.flush()
    assert root.get_children_snapshot()["props"]["text"] == "B"
