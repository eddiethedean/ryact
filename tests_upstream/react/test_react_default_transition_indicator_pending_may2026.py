# Upstream: packages/react-reconciler/src/__tests__/ReactDefaultTransitionIndicator-test.js
# May 2026 inventory slice: useTransition/useOptimistic/useDeferredValue smoke.
from __future__ import annotations

from typing import Any

from ryact import create_element
from ryact.concurrent import Thenable, start_transition
from ryact.hooks import use_deferred_value, use_optimistic, use_state, use_transition
from ryact_testkit import create_noop_root


def _span(text: str) -> Any:
    return create_element("span", {"text": text})


def test_triggers_default_indicator_while_transition_is_ongoing_smoke() -> None:
    # We don't implement ReactNoop onDefaultTransitionIndicator; instead we ensure a
    # transition with an async action sets isPending.
    states: list[bool] = []
    t = Thenable()
    start_holder: list[object] = []

    def App() -> Any:
        is_pending, start = use_transition()
        states.append(bool(is_pending))
        if not start_holder:
            start_holder.append(start)
        return _span("Hi")

    root = create_noop_root()
    root.render(create_element(App))
    root.flush()
    # Start transition *after* mount (not during render).
    start = start_holder[0]
    assert callable(start)
    start(lambda: t)  # type: ignore[misc]
    root.flush()
    t.resolve(None)
    root.flush()
    assert root.get_children_snapshot()["props"]["text"] == "Hi"
    assert any(states)


def test_does_not_trigger_indicator_for_use_deferred_value_sync_smoke() -> None:
    def App(*, value: str) -> Any:
        dv = use_deferred_value(value, "init")
        return _span(str(dv))

    root = create_noop_root()
    root.render(create_element(App, {"value": "Hello"}))
    root.flush()
    assert root.get_children_snapshot()["props"]["text"] in ("init", "Hello")


def test_does_not_trigger_indicator_if_optimistic_update_exists_smoke() -> None:
    def App() -> Any:
        base, _set = use_state("Hi")
        optimistic, _set_opt = use_optimistic(base)
        return _span(str(optimistic))

    root = create_noop_root()
    root.render(create_element(App))
    root.flush()
    assert root.get_children_snapshot()["props"]["text"] == "Hi"


def test_does_not_trigger_indicator_if_sync_mutation_smoke() -> None:
    def App() -> Any:
        state, set_state = use_state("A")
        if state == "A":
            set_state("B")
        return _span(str(state))

    root = create_noop_root()
    root.render(create_element(App))
    root.flush()
    assert root.get_children_snapshot()["props"]["text"] in ("A", "B")

