# Translated from: packages/react-reconciler/src/__tests__/useEffectEvent-test.js
# Burndown v187: interleaved parent/child effect ordering + Activity effect-event mutation.
from __future__ import annotations

from typing import Any, cast

from ryact import (
    activity,
    create_element,
    use_effect,
    use_effect_event,
    use_insertion_effect,
    use_layout_effect,
    use_state,
)
from ryact_testkit import act, create_noop_root, set_act_environment_enabled


def test_fires_all_interleaved_effects_with_use_effect_event_in_correct_order() -> None:
    log: list[str] = []

    def CounterB(props: dict[str, Any]) -> object:
        count = props["count"]
        on_event_parent = props["onEventParent"]

        def on_event() -> str:
            return f"{on_event_parent()} B {count}"

        on_event_fn = use_effect_event(on_event)

        def insertion_create() -> Any:
            log.append(f"Child Insertion Create {on_event_fn()}")

            def insertion_destroy() -> None:
                log.append(f"Child Insertion Destroy {on_event_fn()}")

            return insertion_destroy

        use_insertion_effect(insertion_create)

        def layout_create() -> Any:
            log.append(f"Child Layout Create {on_event_fn()}")

            def layout_destroy() -> None:
                log.append(f"Child Layout Destroy {on_event_fn()}")

            return layout_destroy

        use_layout_effect(layout_create)

        def passive_create() -> Any:
            log.append(f"Child Passive Create {on_event_fn()}")

            def passive_destroy() -> None:
                log.append(f"Child Passive Destroy {on_event_fn()}")

            return passive_destroy

        use_effect(passive_create)
        return None

    def CounterA(props: dict[str, Any]) -> object:
        count = props["count"]

        def on_event() -> str:
            return f"A {count}"

        on_event_fn = use_effect_event(on_event)

        def insertion_create() -> Any:
            log.append(f"Parent Insertion Create: {on_event_fn()}")

            def insertion_cleanup() -> None:
                log.append(f"Parent Insertion Create: {on_event_fn()}")

            return insertion_cleanup

        use_insertion_effect(insertion_create)

        def layout_create() -> Any:
            log.append(f"Parent Layout Create: {on_event_fn()}")

            def layout_cleanup() -> None:
                log.append(f"Parent Layout Cleanup: {on_event_fn()}")

            return layout_cleanup

        use_layout_effect(layout_create)

        def passive_create() -> Any:
            log.append(f"Parent Passive Create: {on_event_fn()}")

            def passive_destroy() -> None:
                log.append(f"Parent Passive Destroy {on_event_fn()}")

            return passive_destroy

        use_effect(passive_create)
        return create_element(
            CounterB,
            {"count": count, "onEventParent": on_event_fn},
        )

    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        with act(flush=root.flush):
            root.render(create_element(CounterA, {"count": 1}))
        assert log == [
            "Child Insertion Create A 1 B 1",
            "Parent Insertion Create: A 1",
            "Child Layout Create A 1 B 1",
            "Parent Layout Create: A 1",
            "Child Passive Create A 1 B 1",
            "Parent Passive Create: A 1",
        ]

        log.clear()
        with act(flush=root.flush):
            root.render(create_element(CounterA, {"count": 2}))
        assert log == [
            "Child Insertion Destroy A 2 B 2",
            "Child Insertion Create A 2 B 2",
            "Child Layout Destroy A 2 B 2",
            "Parent Insertion Create: A 2",
            "Parent Insertion Create: A 2",
            "Parent Layout Cleanup: A 2",
            "Child Layout Create A 2 B 2",
            "Parent Layout Create: A 2",
            "Child Passive Destroy A 2 B 2",
            "Parent Passive Destroy A 2",
            "Child Passive Create A 2 B 2",
            "Parent Passive Create: A 2",
        ]

        log.clear()
        with act(flush=root.flush):
            root.render(None)
        assert log == [
            "Parent Insertion Create: A 2",
            "Parent Layout Cleanup: A 2",
            "Child Insertion Destroy A 2 B 2",
            "Child Layout Destroy A 2 B 2",
            "Parent Passive Destroy A 2",
            "Child Passive Destroy A 2 B 2",
        ]
    finally:
        set_act_environment_enabled(False)


def test_correctly_mutates_effect_event_with_activity_full_flow() -> None:
    log: list[str] = []
    setters: dict[str, Any] = {}

    def CounterB(props: dict[str, Any]) -> object:
        count = props["count"]
        state = props["state"]
        on_event_parent = props["onEventParent"]
        child_state, set_child_state = use_state(1)
        setters["setChildState"] = set_child_state

        def on_event() -> str:
            return f"{on_event_parent()} B {count} {state} {child_state}"

        on_event_fn = use_effect_event(on_event)

        def insertion_create() -> Any:
            log.append(f"Child Insertion Create {on_event_fn()}")
            return lambda: log.append(f"Child Insertion Destroy {on_event_fn()}")

        use_insertion_effect(insertion_create)

        def layout_create() -> Any:
            log.append(f"Child Layout Create {on_event_fn()}")
            return lambda: log.append(f"Child Layout Destroy {on_event_fn()}")

        use_layout_effect(layout_create)

        def passive_create() -> Any:
            log.append(f"Child Passive Create {on_event_fn()}")
            return lambda: log.append(f"Child Passive Destroy {on_event_fn()}")

        use_effect(passive_create)
        return None

    def CounterA(props: dict[str, Any]) -> object:
        count = props["count"]
        hide_child = props["hideChild"]
        state, set_state = use_state(1)
        setters["setState"] = set_state

        def on_event() -> str:
            return f"A {count} {state}"

        on_event_fn = use_effect_event(on_event)

        def insertion_create() -> Any:
            log.append(f"Parent Insertion Create: {on_event_fn()}")
            return lambda: log.append(f"Parent Insertion Create: {on_event_fn()}")

        use_insertion_effect(insertion_create)

        def layout_create() -> Any:
            log.append(f"Parent Layout Create: {on_event_fn()}")
            return lambda: log.append(f"Parent Layout Cleanup: {on_event_fn()}")

        use_layout_effect(layout_create)

        return activity(
            children=create_element(
                CounterB,
                {
                    "count": count,
                    "state": state,
                    "onEventParent": on_event_fn,
                },
            ),
            mode="hidden" if hide_child else "visible",
        )

    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        with act(flush=root.flush):
            root.render(create_element(CounterA, {"count": 1, "hideChild": True}))
        assert log == [
            "Parent Insertion Create: A 1 1",
            "Parent Layout Create: A 1 1",
            "Child Insertion Create A 1 1 B 1 1 1",
        ]

        log.clear()
        with act(flush=root.flush):
            root.render(create_element(CounterA, {"count": 2, "hideChild": True}))
        assert log == [
            "Parent Insertion Create: A 2 1",
            "Parent Insertion Create: A 2 1",
            "Parent Layout Cleanup: A 2 1",
            "Parent Layout Create: A 2 1",
            "Child Insertion Destroy A 2 1 B 2 1 1",
            "Child Insertion Create A 2 1 B 2 1 1",
        ]

        log.clear()
        with act(flush=root.flush):
            cast(Any, setters["setState"])(2)
        assert log == [
            "Parent Insertion Create: A 2 2",
            "Parent Insertion Create: A 2 2",
            "Parent Layout Cleanup: A 2 2",
            "Parent Layout Create: A 2 2",
            "Child Insertion Destroy A 2 2 B 2 2 1",
            "Child Insertion Create A 2 2 B 2 2 1",
        ]

        log.clear()
        with act(flush=root.flush):
            cast(Any, setters["setChildState"])(2)
        assert log == [
            "Child Insertion Destroy A 2 2 B 2 2 2",
            "Child Insertion Create A 2 2 B 2 2 2",
        ]

        log.clear()
        with act(flush=root.flush):
            root.render(create_element(CounterA, {"count": 3, "hideChild": True}))
        assert log == [
            "Parent Insertion Create: A 3 2",
            "Parent Insertion Create: A 3 2",
            "Parent Layout Cleanup: A 3 2",
            "Parent Layout Create: A 3 2",
            "Child Insertion Destroy A 3 2 B 3 2 2",
            "Child Insertion Create A 3 2 B 3 2 2",
        ]

        log.clear()
        with act(flush=root.flush):
            root.render(create_element(CounterA, {"count": 3, "hideChild": False}))
        assert log == [
            "Child Insertion Destroy A 3 2 B 3 2 2",
            "Child Insertion Create A 3 2 B 3 2 2",
            "Parent Insertion Create: A 3 2",
            "Parent Insertion Create: A 3 2",
            "Parent Layout Cleanup: A 3 2",
            "Child Layout Create A 3 2 B 3 2 2",
            "Parent Layout Create: A 3 2",
            "Child Passive Create A 3 2 B 3 2 2",
        ]

        log.clear()
        with act(flush=root.flush):
            root.render(create_element(CounterA, {"count": 3, "hideChild": True}))
        assert log == [
            "Child Layout Destroy A 3 2 B 3 2 2",
            "Parent Insertion Create: A 3 2",
            "Parent Insertion Create: A 3 2",
            "Parent Layout Cleanup: A 3 2",
            "Parent Layout Create: A 3 2",
            "Child Passive Destroy A 3 2 B 3 2 2",
        ]

        log.clear()
        with act(flush=root.flush):
            root.render(None)
        assert log == [
            "Parent Insertion Create: A 3 2",
            "Parent Layout Cleanup: A 3 2",
            "Child Insertion Destroy A 3 2 B 3 2 2",
        ]
    finally:
        setters.clear()
        set_act_environment_enabled(False)
