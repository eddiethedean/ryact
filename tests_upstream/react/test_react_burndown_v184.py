# Translated from:
# - packages/react/src/__tests__/forwardRef-test.internal.js
# - packages/react-reconciler/src/__tests__/useEffectEvent-test.js
# Burndown v184: forwardRef deep class bailout + useEffectEvent context in memo/forwardRef.
from __future__ import annotations

from typing import Any

from ryact import Component, create_element, forward_ref, memo, use_context, use_effect, use_effect_event
from ryact.context import context_provider, create_context
from ryact_testkit import act, create_noop_root, set_act_environment_enabled


def test_should_not_rerun_render_callback_on_deep_setstate() -> None:
    log: list[str] = []
    inst_holder: list[Component] = []

    class Inner(Component):
        def render(self) -> object:
            inst_holder.append(self)
            log.append("Inner")
            return create_element("div", {"ref": self.props.get("forwardedRef")})

    def Middle(props: dict[str, Any]) -> object:
        log.append("Middle")
        return create_element(Inner, props)

    Forward = forward_ref(
        lambda props, ref: (
            log.append("Forward"),
            create_element(Middle, {**props, "forwardedRef": ref}),
        )[1]
    )

    def App() -> object:
        log.append("App")
        return create_element(Forward)

    root = create_noop_root()
    root.render(create_element(App))
    root.flush()
    assert log == ["App", "Forward", "Middle", "Inner"]

    log.clear()
    inst_holder[0].set_state({})
    root.flush()
    assert log == ["Inner"]


def test_reads_latest_context_value_in_memo_components() -> None:
    ctx = create_context("default")
    log: list[str] = []
    handler: list[Any] = [None]

    @memo
    def ContextReader() -> object:
        value = use_context(ctx)
        log.append(f"ContextReader: {value}")

        fire = use_effect_event(lambda: log.append(f"ContextReader (Effect event): {value}"))

        def register() -> None:
            handler[0] = fire

        use_effect(register, ())
        return None

    def App(*, value: str) -> object:
        return context_provider(ctx, value, create_element(ContextReader))

    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        with act(flush=root.flush):
            root.render(create_element(App, {"value": "first"}))
        root.flush()
        assert log == ["ContextReader: first"]

        handler[0]()
        assert log == ["ContextReader: first", "ContextReader (Effect event): first"]

        log.clear()
        with act(flush=root.flush):
            root.render(create_element(App, {"value": "second"}))
        root.flush()
        assert log == ["ContextReader: second"]

        handler[0]()
        assert log == ["ContextReader: second", "ContextReader (Effect event): second"]
    finally:
        set_act_environment_enabled(False)


def test_reads_latest_context_value_in_forwardref_components() -> None:
    ctx = create_context("default")
    log: list[str] = []
    handler: list[Any] = [None]

    def ContextReaderFn(_props: dict[str, Any], _ref: Any) -> object:
        value = use_context(ctx)
        log.append(f"ContextReader: {value}")
        fire = use_effect_event(lambda: log.append(f"ContextReader (Effect event): {value}"))

        def register() -> None:
            handler[0] = fire

        use_effect(register, ())
        return None

    ContextReader = forward_ref(ContextReaderFn)

    def App(*, value: str) -> object:
        return context_provider(ctx, value, create_element(ContextReader))

    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        with act(flush=root.flush):
            root.render(create_element(App, {"value": "first"}))
        root.flush()
        assert log == ["ContextReader: first"]

        handler[0]()
        assert log == ["ContextReader: first", "ContextReader (Effect event): first"]

        log.clear()
        with act(flush=root.flush):
            root.render(create_element(App, {"value": "second"}))
        root.flush()
        assert log == ["ContextReader: second"]

        handler[0]()
        assert log == ["ContextReader: second", "ContextReader (Effect event): second"]
    finally:
        set_act_environment_enabled(False)
