from __future__ import annotations

from typing import Any, Callable

from ryact import (
    create_element,
    memo,
    use_effect,
    use_insertion_effect,
    use_layout_effect,
    use_memo,
    use_state,
)
from ryact_testkit import WarningCapture, act, create_noop_root, set_act_environment_enabled

_Setter = Callable[[Any], None]

def test_usememo_does_not_invoke_memoized_function_during_rerenders_unless_inputs_change() -> None:
    # Upstream: ReactHooksWithNoopRenderer-test.js
    # "should not invoke memoized function during re-renders unless inputs change"
    calls: list[str] = []
    set_tick: list[_Setter | None] = [None]

    def App() -> object:
        tick, s = use_state(0)
        set_tick[0] = s

        def factory() -> str:
            calls.append("factory")
            return "v"

        v = use_memo(factory, (1,))
        return create_element("span", {"children": [f"{v}:{tick}"]})

    set_act_environment_enabled(True)
    root = create_noop_root()
    try:
        with act(flush=root.flush):
            root.render(create_element(App, {}))
        with act(flush=root.flush):
            st = set_tick[0]
            assert st is not None
            st(1)
        with act(flush=root.flush):
            st = set_tick[0]
            assert st is not None
            st(2)
    finally:
        set_act_environment_enabled(False)

    # Factory called only on mount (deps stable).
    assert calls == ["factory"]


def test_useinsertioneffect_assumes_destroy_function_is_function_or_undefined() -> None:
    # Upstream: ReactHooksWithNoopRenderer-test.js
    # "assumes insertion effect destroy function is either a function or undefined"
    set_tick: list[_Setter | None] = [None]

    def App() -> object:
        tick, s = use_state(0)
        set_tick[0] = s

        def eff() -> object:
            # Return a non-callable "cleanup" value; should be ignored safely.
            return 123  # type: ignore[return-value]

        use_insertion_effect(eff, (tick,))
        return create_element("span", {"children": [str(tick)]})

    set_act_environment_enabled(True)
    root = create_noop_root()
    try:
        with act(flush=root.flush):
            root.render(create_element(App, {}))
        with act(flush=root.flush):
            st = set_tick[0]
            assert st is not None
            st(1)
    finally:
        set_act_environment_enabled(False)


def test_uselayouteffect_assumes_destroy_function_is_function_or_undefined() -> None:
    # Upstream: ReactHooksWithNoopRenderer-test.js
    # "assumes layout effect destroy function is either a function or undefined"
    set_tick: list[_Setter | None] = [None]

    def App() -> object:
        tick, s = use_state(0)
        set_tick[0] = s

        def eff() -> object:
            return {"not": "callable"}  # type: ignore[return-value]

        use_layout_effect(eff, (tick,))
        return create_element("span", {"children": [str(tick)]})

    set_act_environment_enabled(True)
    root = create_noop_root()
    try:
        with act(flush=root.flush):
            root.render(create_element(App, {}))
        with act(flush=root.flush):
            st = set_tick[0]
            assert st is not None
            st(1)
    finally:
        set_act_environment_enabled(False)


def test_useinsertioneffect_fires_insertion_effects_before_layout_effects() -> None:
    # Upstream: ReactHooksWithNoopRenderer-test.js
    # "fires insertion effects before layout effects"
    order: list[str] = []

    def App() -> object:
        def ins() -> None:
            order.append("insertion")
            return None

        def lay() -> None:
            order.append("layout")
            return None

        use_insertion_effect(ins, ())
        use_layout_effect(lay, ())
        return create_element("span", {"children": ["ok"]})

    set_act_environment_enabled(True)
    root = create_noop_root()
    try:
        with act(flush=root.flush):
            root.render(create_element(App, {}))
    finally:
        set_act_environment_enabled(False)
    assert order[:2] == ["insertion", "layout"]


def test_useinsertioneffect_warns_when_setstate_is_called_from_insertion_effect_cleanup() -> None:
    # Upstream: ReactHooksWithNoopRenderer-test.js
    # "warns when setState is called from insertion effect cleanup"
    set_tick: list[_Setter | None] = [None]

    def App(*, flip: bool) -> object:
        tick, set_t = use_state(0)
        set_tick[0] = set_t

        def eff() -> object:
            if flip:
                # Only to change deps and trigger cleanup.
                pass

            def cleanup() -> None:
                # This should be inside insertion commit phase.
                set_t(1)

            return cleanup

        use_insertion_effect(eff, (flip,))
        return create_element("span", {"children": [str(tick)]})

    set_act_environment_enabled(True)
    root = create_noop_root()
    try:
        with act(flush=root.flush):
            root.render(create_element(App, {"flip": False}))
        with WarningCapture() as wc, act(flush=root.flush):
            root.render(create_element(App, {"flip": True}))
        wc.assert_any("insertion effect")
    finally:
        set_act_environment_enabled(False)


def test_useeffect_works_with_memo() -> None:
    # Upstream: ReactHooksWithNoopRenderer-test.js
    # "works with memo"
    calls: list[str] = []

    def Inner(*, n: int) -> object:
        def eff() -> object:
            calls.append(f"effect:{n}")
            return None

        use_effect(eff, (n,))
        return create_element("span", {"children": [str(n)]})

    App = memo(Inner)

    set_act_environment_enabled(True)
    root = create_noop_root()
    try:
        with act(flush=root.flush):
            root.render(create_element(App, {"n": 1}))
        # Same props -> memo bailout -> effect should not be re-scheduled.
        with act(flush=root.flush):
            root.render(create_element(App, {"n": 1}))
        with act(flush=root.flush):
            root.render(create_element(App, {"n": 2}))
    finally:
        set_act_environment_enabled(False)

    assert calls == ["effect:1", "effect:2"]
