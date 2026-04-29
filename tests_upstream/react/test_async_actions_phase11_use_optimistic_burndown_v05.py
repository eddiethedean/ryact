from __future__ import annotations

from typing import Any

import pytest

from ryact import create_element, use_optimistic, use_state
from ryact.concurrent import Thenable, start_transition
from ryact_testkit import act, create_noop_root, set_act_environment_enabled


def _span(value: str) -> Any:
    return create_element("span", {"text": value})


def test_useoptimistic_warns_if_outside_of_a_transition() -> None:
    # Upstream: ReactAsyncActions-test.js
    # "useOptimistic warns if outside of a transition"
    set_act_environment_enabled(True)
    root = create_noop_root()
    add_ref: list[Any] = [None]

    def App() -> Any:
        value, add = use_optimistic("A")
        add_ref[0] = add
        return _span(str(value))

    with act(flush=root.flush):
        root.render(create_element(App))

    add = add_ref[0]
    with pytest.warns(RuntimeWarning, match="useOptimistic warns if outside of a transition"):
        add("B")


def test_useoptimistic_passthrough_when_no_pending_transitions() -> None:
    # Upstream: ReactAsyncActions-test.js
    # "regression: when there are no pending transitions, useOptimistic should always return the passthrough value"
    set_act_environment_enabled(True)
    root = create_noop_root()

    def App() -> Any:
        base, _ = use_state("A")
        optimistic, _add = use_optimistic(base)
        return _span(str(optimistic))

    with act(flush=root.flush):
        root.render(create_element(App))
    assert root.container.last_committed["props"]["text"] == "A"


def test_useoptimistic_accepts_a_custom_reducer() -> None:
    # Upstream: ReactAsyncActions-test.js
    # "useOptimistic accepts a custom reducer"
    set_act_environment_enabled(True)
    root = create_noop_root()
    add_ref: list[Any] = [None]

    def reducer(prev: str, action: str) -> str:
        return prev + action

    def App() -> Any:
        optimistic, add = use_optimistic("A", reducer)
        add_ref[0] = add
        return _span(str(optimistic))

    with act(flush=root.flush):
        root.render(create_element(App))
    assert root.container.last_committed["props"]["text"] == "A"

    t = Thenable()
    start_transition(lambda: t)
    add_ref[0]("B")
    root.flush()
    assert root.container.last_committed["props"]["text"] == "AB"
    t.resolve(None)
    root.flush()
    assert root.container.last_committed["props"]["text"] == "A"


def test_useoptimistic_pending_state_and_rebase_on_passthrough() -> None:
    # Upstream: ReactAsyncActions-test.js
    # "useOptimistic can be used to implement a pending state"
    # "useOptimistic rebases pending updates on top of passthrough value"
    set_act_environment_enabled(True)
    root = create_noop_root()
    add_ref: list[Any] = [None]
    set_base_ref: list[Any] = [None]

    def App() -> Any:
        base, set_base = use_state("A")
        set_base_ref[0] = set_base
        optimistic, add = use_optimistic(base)
        add_ref[0] = add
        return _span(str(optimistic))

    with act(flush=root.flush):
        root.render(create_element(App))
    assert root.container.last_committed["props"]["text"] == "A"

    t = Thenable()
    start_transition(lambda: t)
    add_ref[0]("PENDING")
    root.flush()
    assert root.container.last_committed["props"]["text"] == "PENDING"

    # Rebase: update passthrough while pending.
    set_base_ref[0]("B")
    root.flush()
    assert root.container.last_committed["props"]["text"] == "PENDING"

    t.resolve(None)
    root.flush()
    assert root.container.last_committed["props"]["text"] == "B"


def test_multiple_entangled_actions_one_errors_only_affects_that_action() -> None:
    # Upstream: ReactAsyncActions-test.js
    # "if there are multiple entangled actions, and one of them errors, it only affects that action"
    set_act_environment_enabled(True)
    root = create_noop_root()
    add_ref: list[Any] = [None]

    def App() -> Any:
        optimistic, add = use_optimistic("A")
        add_ref[0] = add
        return _span(str(optimistic))

    with act(flush=root.flush):
        root.render(create_element(App))

    t1 = Thenable()
    t2 = Thenable()
    start_transition(lambda: t1)
    add_ref[0]("X1")
    root.flush()
    assert root.container.last_committed["props"]["text"] == "X1"

    start_transition(lambda: t2)
    add_ref[0]("X2")
    root.flush()
    assert root.container.last_committed["props"]["text"] == "X2"

    t1.reject(RuntimeError("boom"))
    root.flush()
    # X2 is still scoped to t2, so it remains.
    assert root.container.last_committed["props"]["text"] == "X2"
    t2.resolve(None)
    root.flush()
    assert root.container.last_committed["props"]["text"] == "A"


def test_useoptimistic_can_update_repeatedly_in_the_same_async_action() -> None:
    # Upstream: ReactAsyncActions-test.js
    # "useOptimistic can update repeatedly in the same async action"
    set_act_environment_enabled(True)
    root = create_noop_root()
    add_ref: list[Any] = [None]

    def App() -> Any:
        optimistic, add = use_optimistic("A")
        add_ref[0] = add
        return _span(str(optimistic))

    with act(flush=root.flush):
        root.render(create_element(App))

    t = Thenable()
    start_transition(lambda: t)
    add_ref[0]("X1")
    add_ref[0]("X2")
    root.flush()
    assert root.container.last_committed["props"]["text"] == "X2"
    t.resolve(None)
    root.flush()
    assert root.container.last_committed["props"]["text"] == "A"


def test_urgent_updates_are_not_blocked_during_an_async_action() -> None:
    # Upstream: ReactAsyncActions-test.js
    # "urgent updates are not blocked during an async action"
    set_act_environment_enabled(True)
    root = create_noop_root()
    add_ref: list[Any] = [None]
    set_urgent_ref: list[Any] = [None]

    def App() -> Any:
        urgent, set_urgent = use_state("U0")
        set_urgent_ref[0] = set_urgent
        optimistic, add = use_optimistic("A")
        add_ref[0] = add
        return _span(f"{urgent}:{optimistic}")

    with act(flush=root.flush):
        root.render(create_element(App))
    assert root.container.last_committed["props"]["text"] == "U0:A"

    t = Thenable()
    start_transition(lambda: t)
    add_ref[0]("P")
    root.flush()
    assert root.container.last_committed["props"]["text"] == "U0:P"

    # Urgent update should still commit while async action pending.
    set_urgent_ref[0]("U1")
    root.flush()
    assert root.container.last_committed["props"]["text"] == "U1:P"

    t.resolve(None)
    root.flush()
    assert root.container.last_committed["props"]["text"] == "U1:A"

