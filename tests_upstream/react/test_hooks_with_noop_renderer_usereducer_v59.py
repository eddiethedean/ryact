from __future__ import annotations

import pytest

from ryact import create_element, use_reducer, use_state
from ryact.hooks import HookError
from ryact_testkit import act, create_noop_root, set_act_environment_enabled


def test_usereducer_lazy_init() -> None:
    # Upstream: ReactHooksWithNoopRenderer-test.js
    # "lazy init"
    init_calls = 0

    def reducer(s: int, a: str) -> int:
        if a == "inc":
            return s + 1
        return s

    def init(x: int) -> int:
        nonlocal init_calls
        init_calls += 1
        return x + 10

    def App() -> object:
        v, _ = use_reducer(reducer, 0, init=init)  # type: ignore[misc]
        return create_element("span", {"children": [str(v)]})

    root = create_noop_root()
    root.render(create_element(App, {}))
    root.render(create_element(App, {}))
    assert init_calls == 1
    assert "10" in str(root.get_children_snapshot())


def test_usereducer_simple_mount_and_update() -> None:
    # Upstream: ReactHooksWithNoopRenderer-test.js
    # "simple mount and update"
    dispatch_ref: list[object] = [None]

    def reducer(s: int, a: str) -> int:
        return s + 1 if a == "inc" else s

    def App() -> object:
        v, d = use_reducer(reducer, 0)  # type: ignore[misc]
        dispatch_ref[0] = d
        return create_element("span", {"children": [str(v)]})

    set_act_environment_enabled(True)
    root = create_noop_root()
    try:
        with act(flush=root.flush):
            root.render(create_element(App, {}))
        assert "0" in str(root.get_children_snapshot())
        with act(flush=root.flush):
            dispatch_ref[0]("inc")  # type: ignore[misc]
    finally:
        set_act_environment_enabled(False)
    assert "1" in str(root.get_children_snapshot())


def test_usereducer_does_not_eagerly_bail_out_of_state_updates() -> None:
    # Upstream: ReactHooksWithNoopRenderer-test.js
    # "useReducer does not eagerly bail out of state updates"
    #
    # Key intent: do not drop a "potentially no-op" action at dispatch time because
    # other updates in the same batch (e.g. props/state changes) may make it relevant.
    dispatch_ref: list[object] = [None]
    set_mul_ref: list[object] = [None]

    def App() -> object:
        mul, set_mul = use_state(0)
        set_mul_ref[0] = set_mul

        def reducer(s: int, a: str) -> int:
            if a == "addMul":
                return s + mul
            return s

        v, d = use_reducer(reducer, 0)  # type: ignore[misc]
        dispatch_ref[0] = d
        return create_element("span", {"children": [str(v)]})

    set_act_environment_enabled(True)
    root = create_noop_root()
    try:
        with act(flush=root.flush):
            root.render(create_element(App, {}))
        # In one batch: dispatch when mul==0 (would appear no-op if computed eagerly),
        # then update mul -> 5 before the batch flushes. The reducer action should apply.
        with act(flush=root.flush):
            dispatch_ref[0]("addMul")  # type: ignore[misc]
            set_mul_ref[0](5)  # type: ignore[misc]
    finally:
        set_act_environment_enabled(False)
    assert "5" in str(root.get_children_snapshot())


def test_usereducer_does_not_replay_previous_no_op_actions_when_props_change() -> None:
    # Upstream: ReactHooksWithNoopRenderer-test.js
    # "useReducer does not replay previous no-op actions when props change"
    dispatch_ref: list[object] = [None]

    def App(*, mul: int) -> object:
        def reducer(s: int, a: str) -> int:
            if a == "addMul":
                return s + int(mul)
            return s

        v, d = use_reducer(reducer, 0)  # type: ignore[misc]
        dispatch_ref[0] = d
        return create_element("span", {"children": [str(v)]})

    set_act_environment_enabled(True)
    root = create_noop_root()
    try:
        with act(flush=root.flush):
            root.render(create_element(App, {"mul": 0}))
        with act(flush=root.flush):
            dispatch_ref[0]("addMul")  # type: ignore[misc]
        assert "0" in str(root.get_children_snapshot())
        # If the previous no-op action were incorrectly replayed against the new reducer/props,
        # we'd observe state jump to 5 here. It must remain 0.
        with act(flush=root.flush):
            root.render(create_element(App, {"mul": 5}))
    finally:
        set_act_environment_enabled(False)
    assert "0" in str(root.get_children_snapshot())


def test_usereducer_does_not_replay_previous_no_op_actions_when_other_state_changes() -> None:
    # Upstream: ReactHooksWithNoopRenderer-test.js
    # "useReducer does not replay previous no-op actions when other state changes"
    dispatch_ref: list[object] = [None]
    bump_ref: list[object] = [None]

    def App() -> object:
        mul, set_mul = use_state(0)
        bump_ref[0] = lambda: set_mul(lambda x: x + 5)  # type: ignore[misc]

        def reducer(s: int, a: str) -> int:
            if a == "addMul":
                return s + mul
            return s

        v, d = use_reducer(reducer, 0)  # type: ignore[misc]
        dispatch_ref[0] = d
        return create_element("span", {"children": [str(v)]})

    set_act_environment_enabled(True)
    root = create_noop_root()
    try:
        with act(flush=root.flush):
            root.render(create_element(App, {}))
        with act(flush=root.flush):
            dispatch_ref[0]("addMul")  # type: ignore[misc]
        assert "0" in str(root.get_children_snapshot())
        # Change unrelated state; old no-op action must not be replayed.
        with act(flush=root.flush):
            bump_ref[0]()  # type: ignore[misc]
    finally:
        set_act_environment_enabled(False)
    assert "0" in str(root.get_children_snapshot())


def test_usereducer_applies_potential_no_op_changes_if_made_relevant_by_other_updates_in_the_batch() -> None:
    # Upstream: ReactHooksWithNoopRenderer-test.js
    # "useReducer applies potential no-op changes if made relevant by other updates in the batch"
    dispatch_ref: list[object] = [None]
    set_mul_ref: list[object] = [None]

    def App() -> object:
        mul, set_mul = use_state(0)
        set_mul_ref[0] = set_mul

        def reducer(s: int, a: str) -> int:
            if a == "addMul":
                return s + mul
            return s

        v, d = use_reducer(reducer, 0)  # type: ignore[misc]
        dispatch_ref[0] = d
        return create_element("span", {"children": [str(v)]})

    set_act_environment_enabled(True)
    root = create_noop_root()
    try:
        with act(flush=root.flush):
            root.render(create_element(App, {}))
        with act(flush=root.flush):
            # Same pattern as upstream: enqueue a "potential no-op" update, then
            # make it relevant in the same batch.
            dispatch_ref[0]("addMul")  # type: ignore[misc]
            set_mul_ref[0](7)  # type: ignore[misc]
    finally:
        set_act_environment_enabled(False)
    assert "7" in str(root.get_children_snapshot())

