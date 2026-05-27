# Translated from: packages/react-reconciler/src/__tests__/ReactFlushSync-test.js
# Burndown v143: flushSync passive ordering and nested transition priority.
from __future__ import annotations

from typing import Any, cast

import pytest
from ryact import create_element, start_transition, use_effect, use_state
from ryact_testkit import act, create_noop_root, set_act_environment_enabled


def _text(log: list[str], label: str) -> Any:
    log.append(label)
    return create_element("span", {"text": label})


def test_flushes_passive_effects_synchronously_when_they_are_the_result_of_a_sync_render() -> None:
    log: list[str] = []

    def App() -> object:
        def eff() -> None:
            log.append("Effect")

        use_effect(eff, ())
        return _text(log, "Child")

    root = create_noop_root()
    root.flush_sync(lambda: root.render(create_element(App)))
    assert log == ["Child", "Effect"]


def test_does_not_flush_passive_effects_synchronously_when_they_arent_the_result_of_a_sync_render() -> None:
    log: list[str] = []
    setter: list[Any] = [None]

    def App() -> object:
        v, set_v = use_state(0)
        setter[0] = set_v

        def eff() -> None:
            log.append(f"Effect {v}")

        use_effect(eff, (v,))
        return _text(log, f"Child {v}")

    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        with act(flush=root.flush):
            root.render(create_element(App))
        assert log == ["Child 0", "Effect 0"]
        log.clear()
        with act(flush=root.flush):
            cast(Any, setter[0])(1)
        assert log == ["Child 1", "Effect 1"]
        log.clear()
        root.flush_sync(None)
        assert log == []
    finally:
        set_act_environment_enabled(False)


def test_does_not_flush_pending_passive_effects() -> None:
    log: list[str] = []
    setter: list[Any] = [None]

    def App() -> object:
        v, set_v = use_state(0)
        setter[0] = set_v

        def eff() -> None:
            log.append(f"Effect {v}")

        use_effect(eff, (v,))
        return _text(log, f"Child {v}")

    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        with act(flush=root.flush):
            root.render(create_element(App))
        assert log == ["Child 0", "Effect 0"]
        log.clear()
        root.flush_sync(lambda: cast(Any, setter[0])(1))
        assert log == ["Child 1"]
        root.flush_sync(None)
        assert log == ["Child 1"]
        root.flush()
        assert log == ["Child 1", "Effect 1"]
    finally:
        set_act_environment_enabled(False)


def test_does_not_flush_passive_effects_synchronously_after_render_in_legacy_mode() -> None:
    log: list[str] = []

    def App() -> object:
        def eff() -> None:
            log.append("Effect")

        use_effect(eff, ())
        return _text(log, "Child")

    root = create_noop_root(legacy=True)
    root.flush_sync(lambda: root.render(create_element(App)))
    assert log == ["Child"]
    root.flush()
    assert log == ["Child", "Effect"]


def test_flushes_pending_passive_effects_before_scope_is_called_in_legacy_mode() -> None:
    log: list[str] = []
    current_step = {"v": 0}

    def App(*, step: int) -> object:
        def eff() -> None:
            current_step["v"] = step
            log.append(f"Effect: {step}")

        use_effect(eff, (step,))
        return _text(log, str(step))

    root = create_noop_root(legacy=True)
    root.flush_sync(lambda: root.render(create_element(App, {"step": 1})))
    assert log == ["1"]

    root.flush_sync(lambda: root.render(create_element(App, {"step": current_step["v"] + 1})))
    assert log == ["1", "Effect: 1", "2"]
    root.flush()
    assert log == ["1", "Effect: 1", "2", "Effect: 2"]


def test_supports_nested_flushsync_with_starttransition() -> None:
    log: list[str] = []
    setters: dict[str, Any] = {}

    def App() -> object:
        sync_state, set_sync = use_state(0)
        state, set_state = use_state(0)
        setters["sync"] = set_sync
        setters["async"] = set_state

        return _text(log, f"{sync_state}, {state}")

    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        with act(flush=root.flush):
            root.render(create_element(App))
        assert log == ["0, 0"]

        log.clear()

        def outer() -> None:
            def inner_transition() -> None:
                cast(Any, setters["async"])(1)

                def inner_sync() -> None:
                    cast(Any, setters["sync"])(1)

                root.flush_sync(inner_sync)

            start_transition(inner_transition)

        root.flush_sync(outer)
        assert log == ["1, 0"]
        with act(flush=root.flush):
            pass
        assert log[-1] == "1, 1"
    finally:
        set_act_environment_enabled(False)


def test_does_not_flush_non_discrete_passive_effects_when_flushing_sync_update() -> None:
    # HooksWithNoopRenderer parity: sync setState inside flushSync defers that commit's passives.
    log: list[str] = []
    setter: list[Any] = [None]

    def App() -> object:
        v, set_v = use_state(0)
        setter[0] = set_v

        def eff() -> None:
            log.append(f"passive {v}")

        use_effect(eff, (v,))
        return create_element("span", {"text": f"ok {v}"})

    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        with act(flush=root.flush):
            root.render(create_element(App))
        assert log == ["passive 0"]
        log.clear()
        root.flush_sync(lambda: setter[0](1))
        assert log == []
        root.flush()
        assert log == ["passive 1"]
    finally:
        set_act_environment_enabled(False)


@pytest.mark.skip(reason="Deferred: requires multi-root noop renderToRootWithID + AggregateError")
def test_completely_exhausts_synchronous_work_queue_even_if_something_throws() -> None:
    pass


@pytest.mark.skip(reason="Deferred: requires DOM createRoot + transition paint + DEV flushSync-in-effect warning")
def test_changes_priority_of_updates_in_useeffect() -> None:
    pass
