# Translated from: packages/react-reconciler/src/__tests__/useEffectEvent-test.js
# Burndown v186: useEffectEvent + Activity hidden prerender insertion semantics.
from __future__ import annotations

from typing import Any

from ryact import (
    activity,
    create_element,
    use_effect_event,
    use_insertion_effect,
    use_layout_effect,
    use_state,
)
from ryact_testkit import act, create_noop_root, set_act_environment_enabled


def test_effect_events_are_fresh_inside_activity() -> None:
    log: list[str] = []

    def Child(props: dict[str, Any]) -> object:
        value = props["value"]
        get_value = use_effect_event(lambda: value)

        def insertion_create() -> Any:
            log.append(f"insertion create: {get_value()}")

            def insertion_destroy() -> None:
                log.append(f"insertion destroy: {get_value()}")

            return insertion_destroy

        use_insertion_effect(insertion_create)

        def layout_create() -> Any:
            log.append(f"layout create: {get_value()}")

            def layout_destroy() -> None:
                log.append(f"layout destroy: {get_value()}")

            return layout_destroy

        use_layout_effect(layout_create)
        log.append(f"render: {value}")
        return None

    def App(props: dict[str, Any]) -> object:
        return activity(children=create_element(Child, {"value": props["value"]}), mode=props["mode"])

    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        with act(flush=root.flush):
            root.render(create_element(App, {"value": 1, "mode": "hidden"}))
        assert log == ["render: 1", "insertion create: 1"]

        log.clear()
        with act(flush=root.flush):
            root.render(create_element(App, {"value": 2, "mode": "hidden"}))
        assert log == ["render: 2", "insertion destroy: 2", "insertion create: 2"]

        log.clear()
        with act(flush=root.flush):
            root.render(create_element(App, {"value": 2, "mode": "visible"}))
        assert log == ["render: 2", "insertion destroy: 2", "insertion create: 2", "layout create: 2"]
    finally:
        set_act_environment_enabled(False)


def test_correctly_mutates_effect_event_with_activity() -> None:
    log: list[str] = []

    def CounterB(props: dict[str, Any]) -> object:
        count = props["count"]
        state = props["state"]
        on_event_parent = props["onEventParent"]
        child_state = props["childState"]
        on_event = use_effect_event(lambda: f"{on_event_parent()} B {count} {state} {child_state}")

        def insertion_create() -> Any:
            log.append(f"Child Insertion Create {on_event()}")
            return None

        use_insertion_effect(insertion_create)
        return None

    def CounterA(props: dict[str, Any]) -> object:
        count = props["count"]
        hide_child = props["hideChild"]
        state, _set_state = use_state(1)
        on_event = use_effect_event(lambda: f"A {count} {state}")

        def parent_insertion_create() -> Any:
            log.append(f"Parent Insertion Create: {on_event()}")
            return None

        use_insertion_effect(parent_insertion_create)

        def parent_layout_create() -> Any:
            log.append(f"Parent Layout Create: {on_event()}")
            return None

        use_layout_effect(parent_layout_create)
        return activity(
            children=create_element(
                CounterB,
                {
                    "count": count,
                    "state": state,
                    "childState": 1,
                    "onEventParent": on_event,
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
            "Child Insertion Create A 1 1 B 1 1 1",
            "Parent Insertion Create: A 1 1",
            "Parent Layout Create: A 1 1",
        ]
    finally:
        set_act_environment_enabled(False)
