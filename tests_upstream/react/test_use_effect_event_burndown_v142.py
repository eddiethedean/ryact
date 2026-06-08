# Translated from: packages/react-reconciler/src/__tests__/useEffectEvent-test.js
# Burndown v142: core useEffectEvent semantics (noop harness).
from __future__ import annotations

from typing import Any, cast

import pytest
from ryact import (
    PureComponent,
    create_element,
    create_ref,
    fragment,
    use_effect,
    use_effect_event,
    use_insertion_effect,
    use_layout_effect,
    use_state,
)
from ryact_testkit import act, create_noop_root, set_act_environment_enabled


def _text(log: list[str], label: str) -> Any:
    log.append(label)
    return create_element("span", {"text": label})


def _logged_text(*, log: list[str], label: str) -> Any:
    def Text() -> object:
        log.append(label)
        return create_element("span", {"text": label})

    return create_element(Text)


def _texts_in_snapshot(node: Any) -> list[str]:
    if node is None:
        return []
    if isinstance(node, str):
        return [node]
    if isinstance(node, dict):
        out: list[str] = []
        props = node.get("props") or {}
        if "text" in props:
            out.append(str(props["text"]))
        for ch in props.get("children") or []:
            out.extend(_texts_in_snapshot(ch))
        return out
    if isinstance(node, list):
        merged: list[str] = []
        for item in node:
            merged.extend(_texts_in_snapshot(item))
        return merged
    return []


def _assert_snapshot_texts(root: Any, expected: list[str]) -> None:
    snap = root.get_children_snapshot()
    assert _texts_in_snapshot(snap) == expected


def test_memoizes_basic_case_correctly() -> None:
    log: list[str] = []
    button = create_ref()

    class IncrementButton(PureComponent):
        def increment(self) -> None:
            on_click = self.props.get("onClick")
            if callable(on_click):
                on_click()

        def render(self) -> object:
            return _text(log, "Increment")

    def Counter(*, increment_by: int) -> object:
        count, update_count = use_state(0)
        on_click = use_effect_event(lambda: update_count(lambda c: c + increment_by))
        return fragment(
            create_element(
                IncrementButton,
                {"onClick": lambda: on_click(), "ref": button},
            ),
            _logged_text(log=log, label=f"Count: {count}"),
        )

    root = create_noop_root()
    root.render(create_element(Counter, {"increment_by": 1}))
    root.flush()
    assert log == ["Increment", "Count: 0"]
    _assert_snapshot_texts(root, ["Increment", "Count: 0"])

    with act(flush=root.flush):
        cast(IncrementButton, button.current).increment()
    assert log[-2:] == ["Increment", "Count: 1"]
    _assert_snapshot_texts(root, ["Increment", "Count: 1"])

    with act(flush=root.flush):
        cast(IncrementButton, button.current).increment()
    assert log[-2:] == ["Increment", "Count: 2"]

    root.render(create_element(Counter, {"increment_by": 10}))
    root.flush()
    assert log[-2:] == ["Increment", "Count: 2"]

    with act(flush=root.flush):
        cast(IncrementButton, button.current).increment()
    assert log[-2:] == ["Increment", "Count: 12"]


def test_can_be_defined_more_than_once() -> None:
    log: list[str] = []
    button = create_ref()

    class IncrementButton(PureComponent):
        def increment(self) -> None:
            on_click = self.props.get("onClick")
            if callable(on_click):
                on_click()

        def multiply(self) -> None:
            on_enter = self.props.get("onMouseEnter")
            if callable(on_enter):
                on_enter()

        def render(self) -> object:
            return _text(log, "Increment")

    def Counter(*, increment_by: int) -> object:
        count, update_count = use_state(0)
        on_click = use_effect_event(lambda: update_count(lambda c: c + increment_by))
        on_mouse_enter = use_effect_event(lambda: update_count(lambda c: c * increment_by))
        return fragment(
            create_element(
                IncrementButton,
                {
                    "onClick": lambda: on_click(),
                    "onMouseEnter": lambda: on_mouse_enter(),
                    "ref": button,
                },
            ),
            _logged_text(log=log, label=f"Count: {count}"),
        )

    root = create_noop_root()
    root.render(create_element(Counter, {"increment_by": 5}))
    root.flush()
    assert log == ["Increment", "Count: 0"]

    with act(flush=root.flush):
        cast(IncrementButton, button.current).increment()
    assert log[-2:] == ["Increment", "Count: 5"]

    with act(flush=root.flush):
        cast(IncrementButton, button.current).multiply()
    assert log[-2:] == ["Increment", "Count: 25"]


def test_does_not_preserve_this_in_event_functions() -> None:
    log: list[str] = []
    button = create_ref()

    class GreetButton(PureComponent):
        def greet(self) -> None:
            on_click = self.props.get("onClick")
            if callable(on_click):
                on_click()

        def render(self) -> object:
            hello = str(self.props.get("hello", ""))
            return _text(log, f"Say {hello}")

    def Greeter(*, hello: str) -> object:
        greeting, update_greeting = use_state(f"Seb says {hello}")

        def greet_impl() -> None:
            update_greeting(f"undefined says {hello}")

        on_click = use_effect_event(greet_impl)
        return fragment(
            create_element(
                GreetButton,
                {"hello": hello, "onClick": lambda: on_click(), "ref": button},
            ),
            _logged_text(log=log, label=f"Greeting: {greeting}"),
        )

    root = create_noop_root()
    root.render(create_element(Greeter, {"hello": "hej"}))
    root.flush()
    assert "Say hej" in log
    assert "Greeting: Seb says hej" in log

    with act(flush=root.flush):
        cast(GreetButton, button.current).greet()
    assert "Greeting: undefined says hej" in log


def test_throws_when_called_in_render() -> None:
    log: list[str] = []

    class IncrementButton(PureComponent):
        def render(self) -> object:
            on_click = self.props.get("onClick")
            if callable(on_click):
                on_click()
            return _text(log, "Increment")

    def Counter(*, increment_by: int) -> object:
        count, update_count = use_state(0)
        on_click = use_effect_event(lambda: update_count(lambda c: c + increment_by))
        return fragment(
            create_element(IncrementButton, {"onClick": lambda: on_click()}),
            _logged_text(log=log, label=f"Count: {count}"),
        )

    root = create_noop_root()
    with pytest.raises(RuntimeError, match="can't be called during rendering"):
        root.render(create_element(Counter, {"increment_by": 1}))
    assert log == []


def test_use_layout_effect_shouldnt_re_fire_when_event_handlers_change() -> None:
    log: list[str] = []
    button = create_ref()

    class IncrementButton(PureComponent):
        def increment(self) -> None:
            on_click = self.props.get("onClick")
            if callable(on_click):
                on_click()

        def render(self) -> object:
            return _text(log, "Increment")

    def Counter(*, increment_by: int) -> object:
        count, update_count = use_state(0)
        increment = use_effect_event(
            lambda amount=None: update_count(lambda c: c + (amount if amount is not None else increment_by))
        )

        def layout_eff() -> None:
            log.append(f"Effect: by {increment_by * 2}")
            increment(increment_by * 2)

        use_layout_effect(layout_eff, (increment_by,))
        return fragment(
            create_element(
                IncrementButton,
                {"onClick": lambda: increment(), "ref": button},
            ),
            _logged_text(log=log, label=f"Count: {count}"),
        )

    root = create_noop_root()
    root.render(create_element(Counter, {"increment_by": 1}))
    root.flush()
    assert log == ["Increment", "Count: 0", "Effect: by 2", "Increment", "Count: 2"]

    log.clear()
    with act(flush=root.flush):
        cast(IncrementButton, button.current).increment()
    assert log == ["Increment", "Count: 3"]

    log.clear()
    with act(flush=root.flush):
        cast(IncrementButton, button.current).increment()
    assert log == ["Increment", "Count: 4"]

    log.clear()
    root.render(create_element(Counter, {"increment_by": 10}))
    root.flush()
    assert log == ["Increment", "Count: 4", "Effect: by 20", "Increment", "Count: 24"]

    log.clear()
    with act(flush=root.flush):
        cast(IncrementButton, button.current).increment()
    assert log == ["Increment", "Count: 34"]


def test_use_effect_shouldnt_re_fire_when_event_handlers_change() -> None:
    log: list[str] = []
    button = create_ref()

    class IncrementButton(PureComponent):
        def increment(self) -> None:
            on_click = self.props.get("onClick")
            if callable(on_click):
                on_click()

        def render(self) -> object:
            return _text(log, "Increment")

    def Counter(*, increment_by: int) -> object:
        count, update_count = use_state(0)
        increment = use_effect_event(
            lambda amount=None: update_count(lambda c: c + (amount if amount is not None else increment_by))
        )

        def passive_eff() -> None:
            log.append(f"Effect: by {increment_by * 2}")
            increment(increment_by * 2)

        use_effect(passive_eff, (increment_by,))
        return fragment(
            create_element(
                IncrementButton,
                {"onClick": lambda: increment(), "ref": button},
            ),
            _logged_text(log=log, label=f"Count: {count}"),
        )

    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        with act(flush=root.flush):
            root.render(create_element(Counter, {"increment_by": 1}))
        root.flush()
        assert log == ["Increment", "Count: 0", "Effect: by 2", "Increment", "Count: 2"]

        log.clear()
        with act(flush=root.flush):
            cast(IncrementButton, button.current).increment()
        assert log == ["Increment", "Count: 3"]

        log.clear()
        with act(flush=root.flush):
            cast(IncrementButton, button.current).increment()
        assert log == ["Increment", "Count: 4"]

        log.clear()
        with act(flush=root.flush):
            root.render(create_element(Counter, {"increment_by": 10}))
        root.flush()
        assert log == ["Increment", "Count: 4", "Effect: by 20", "Increment", "Count: 24"]

        log.clear()
        with act(flush=root.flush):
            cast(IncrementButton, button.current).increment()
        assert log == ["Increment", "Count: 34"]
    finally:
        set_act_environment_enabled(False)


def test_is_stable_in_a_custom_hook() -> None:
    log: list[str] = []
    button = create_ref()

    class IncrementButton(PureComponent):
        def increment(self) -> None:
            on_click = self.props.get("onClick")
            if callable(on_click):
                on_click()

        def render(self) -> object:
            return _text(log, "Increment")

    def use_count(increment_by: int) -> tuple[int, Any]:
        count, update_count = use_state(0)
        increment = use_effect_event(
            lambda amount=None: update_count(lambda c: c + (amount if amount is not None else increment_by))
        )
        return count, increment

    def Counter(*, increment_by: int) -> object:
        count, increment = use_count(increment_by)

        def passive_eff() -> None:
            log.append(f"Effect: by {increment_by * 2}")
            increment(increment_by * 2)

        use_effect(passive_eff, (increment_by,))
        return fragment(
            create_element(
                IncrementButton,
                {"onClick": lambda: increment(), "ref": button},
            ),
            _logged_text(log=log, label=f"Count: {count}"),
        )

    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        with act(flush=root.flush):
            root.render(create_element(Counter, {"increment_by": 1}))
        root.flush()
        assert log == ["Increment", "Count: 0", "Effect: by 2", "Increment", "Count: 2"]

        log.clear()
        with act(flush=root.flush):
            cast(IncrementButton, button.current).increment()
        assert log == ["Increment", "Count: 3"]

        log.clear()
        with act(flush=root.flush):
            cast(IncrementButton, button.current).increment()
        assert log == ["Increment", "Count: 4"]

        log.clear()
        root.render(create_element(Counter, {"increment_by": 10}))
        root.flush()
        assert log == ["Increment", "Count: 4", "Effect: by 20", "Increment", "Count: 24"]
    finally:
        set_act_environment_enabled(False)


def test_is_mutated_before_all_other_effects() -> None:
    log: list[str] = []

    def Counter(*, value: int) -> object:
        def insertion_eff() -> None:
            log.append(f"Effect value: {value}")
            increment()

        use_insertion_effect(insertion_eff, (value,))

        increment = use_effect_event(lambda: log.append(f"Event value: {value}"))
        return None

    root = create_noop_root()
    root.render(create_element(Counter, {"value": 1}))
    root.flush()
    assert log == ["Effect value: 1", "Event value: 1"]

    log.clear()
    with act(flush=root.flush):
        root.render(create_element(Counter, {"value": 2}))
    root.flush()
    assert log == ["Effect value: 2", "Event value: 2"]


def test_doesnt_provide_a_stable_identity() -> None:
    log: list[str] = []

    def Counter(*, should_render: bool, value: int) -> object:
        on_click = use_effect_event(lambda: log.append(f"onClick, shouldRender={should_render}, value={value}"))

        use_effect(lambda: on_click(), (on_click,))
        use_effect(lambda: on_click(), (should_render,))
        return None

    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        with act(flush=root.flush):
            root.render(create_element(Counter, {"should_render": True, "value": 0}))
        root.flush()
        assert log.count("onClick, shouldRender=True, value=0") == 2

        log.clear()
        with act(flush=root.flush):
            root.render(create_element(Counter, {"should_render": True, "value": 1}))
        root.flush()
        assert log == ["onClick, shouldRender=True, value=1"]

        log.clear()
        with act(flush=root.flush):
            root.render(create_element(Counter, {"should_render": False, "value": 2}))
        root.flush()
        assert log.count("onClick, shouldRender=False, value=2") == 2
    finally:
        set_act_environment_enabled(False)


def test_event_handlers_always_see_the_latest_committed_value() -> None:
    committed_event_handler: list[Any] = [None]

    def App(*, value: int) -> object:
        event = use_effect_event(lambda: f"Value seen by useEffectEvent: {value}")

        def register_eff() -> Any:
            committed_event_handler[0] = event

            def cleanup() -> None:
                committed_event_handler[0] = None

            return cleanup

        use_effect(register_eff, ())
        return create_element("span", {"text": f"Latest rendered value {value}"})

    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        with act(flush=root.flush):
            root.render(create_element(App, {"value": 1}))
        root.flush()
        snap = root.get_children_snapshot()
        assert snap["props"]["text"] == "Latest rendered value 1"
        handler = committed_event_handler[0]
        assert callable(handler)
        assert handler() == "Value seen by useEffectEvent: 1"

        with act(flush=root.flush):
            root.render(create_element(App, {"value": 2}))
        root.flush()
        snap2 = root.get_children_snapshot()
        assert snap2["props"]["text"] == "Latest rendered value 2"
        assert handler() == "Value seen by useEffectEvent: 2"
    finally:
        set_act_environment_enabled(False)
