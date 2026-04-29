from __future__ import annotations

from typing import Any

from ryact import create_element, use_transition
from ryact.concurrent import Thenable
from ryact_testkit import act, create_noop_root, set_act_environment_enabled


def _span(value: str) -> Any:
    return create_element("span", {"text": value})


def test_is_pending_remains_true_until_async_action_finishes() -> None:
    # Upstream: ReactAsyncActions-test.js
    # "isPending remains true until async action finishes"
    set_act_environment_enabled(True)
    root = create_noop_root()
    start_ref: list[Any] = [None]
    thenable = Thenable()

    def App() -> Any:
        pending, start = use_transition()
        start_ref[0] = start
        return _span("pending" if pending else "idle")

    with act(flush=root.flush):
        root.render(create_element(App))
    assert root.container.last_committed["props"]["text"] == "idle"

    def action() -> Thenable:
        return thenable

    start = start_ref[0]
    assert callable(start)

    start(action)
    root.flush()
    assert root.container.last_committed["props"]["text"] == "pending"

    thenable.resolve(None)
    root.flush()
    assert root.container.last_committed["props"]["text"] == "idle"

