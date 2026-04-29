from __future__ import annotations

from typing import Any

from ryact import create_element, use_state
from ryact.concurrent import Transition, set_transition_tracing_callbacks, start_transition
from ryact_testkit import act, create_noop_root, set_act_environment_enabled


def _span(value: str) -> Any:
    return create_element("span", {"text": value})


def test_transition_callbacks_work_for_multiple_roots() -> None:
    # Upstream: ReactTransitionTracing-test.js
    # "transition callbacks work for multiple roots"
    set_act_environment_enabled(True)
    events: list[str] = []
    set_transition_tracing_callbacks(
        on_transition_start=lambda name: events.append(f"start:{name}"),
        on_transition_complete=lambda name: events.append(f"complete:{name}"),
    )
    try:
        r1 = create_noop_root()
        r2 = create_noop_root()

        with act(flush=r1.flush):
            r1.render(_span("r1"))
        with act(flush=r2.flush):
            r2.render(_span("r2"))

        start_transition(lambda: None, transition=Transition(name="t-multi"))
        r1.flush()
        r2.flush()
        assert events[:1] == ["start:t-multi"]
        assert "complete:t-multi" in events
    finally:
        set_transition_tracing_callbacks()


def test_discrete_events_smoke() -> None:
    # Upstream: ReactTransitionTracing-test.js
    # "discrete events"
    set_act_environment_enabled(True)
    events: list[str] = []
    set_transition_tracing_callbacks(
        on_transition_start=lambda name: events.append(f"start:{name}"),
        on_transition_complete=lambda name: events.append(f"complete:{name}"),
    )
    try:
        root = create_noop_root()

        def App() -> Any:
            v, set_v = use_state("A")
            return create_element(
                "div",
                {
                    "text": v,
                    "set_v": set_v,
                },
            )

        with act(flush=root.flush):
            root.render(create_element(App))

        start_transition(lambda: None, transition=Transition(name="t1"))
        root.flush()
        assert events == ["start:t1", "complete:t1"]
    finally:
        set_transition_tracing_callbacks()

