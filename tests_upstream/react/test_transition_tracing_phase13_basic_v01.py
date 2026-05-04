from __future__ import annotations

from typing import Any

from ryact import create_element, use_state
from ryact.concurrent import Transition, set_transition_tracing_callbacks, start_transition
from ryact_testkit import act, create_noop_root, set_act_environment_enabled


def _span(value: str) -> Any:
    return create_element("span", {"text": value})


def test_should_not_call_callbacks_when_transition_is_not_defined() -> None:
    # Upstream: ReactTransitionTracing-test.js
    # "should not call callbacks when transition is not defined"
    events: list[str] = []

    set_transition_tracing_callbacks(
        on_transition_start=lambda name: events.append(f"start:{name}"),
        on_transition_complete=lambda name: events.append(f"complete:{name}"),
    )

    # No transition object passed -> tracing callbacks should not fire.
    start_transition(lambda: None)
    assert events == []
    set_transition_tracing_callbacks()


def test_multiple_updates_in_transition_callback_only_one_start_complete() -> None:
    # Upstream: ReactTransitionTracing-test.js
    # "multiple updates in transition callback should only result in one transitionStart/transitionComplete call"
    events: list[str] = []
    root = create_noop_root()
    setter_ref: list[Any] = [None]
    set_act_environment_enabled(True)

    set_transition_tracing_callbacks(
        on_transition_start=lambda name: events.append(f"start:{name}"),
        on_transition_complete=lambda name: events.append(f"complete:{name}"),
    )

    def App() -> Any:
        value, set_value = use_state("A")
        setter_ref[0] = set_value
        return _span(str(value))

    with act(flush=root.flush):
        root.render(create_element(App))
    assert root.container.last_committed_as_dict()["props"]["text"] == "A"

    def action() -> None:
        set_value = setter_ref[0]
        set_value("B")
        set_value("C")

    # Start a named transition and flush. Despite two updates, we should only get
    # one start/complete pair.
    start_transition(action, transition=Transition(name="t1"))
    root.flush()
    assert root.container.last_committed_as_dict()["props"]["text"] == "C"
    assert events == ["start:t1", "complete:t1"]
    set_transition_tracing_callbacks()
