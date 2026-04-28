from __future__ import annotations

from ryact import create_element, use_effect, use_state
from ryact_testkit import WarningCapture, act, create_noop_root, set_act_environment_enabled


def test_useeffect_assumes_passive_effect_destroy_function_is_function_or_undefined() -> None:
    # Upstream: ReactHooksWithNoopRenderer-test.js
    # "assumes passive effect destroy function is either a function or undefined"
    set_tick: list[object] = [None]

    def App() -> object:
        tick, s = use_state(0)
        set_tick[0] = s

        def eff() -> object:
            # Return a non-callable cleanup value; should be ignored safely.
            return 123  # type: ignore[return-value]

        use_effect(eff, (tick,))
        return create_element("span", {"children": [str(tick)]})

    set_act_environment_enabled(True)
    root = create_noop_root()
    try:
        with act(flush=root.flush):
            root.render(create_element(App, {}))
        with act(flush=root.flush):
            set_tick[0](1)  # type: ignore[misc]
    finally:
        set_act_environment_enabled(False)


def test_useeffect_unmounts_previous_effect() -> None:
    # Upstream: ReactHooksWithNoopRenderer-test.js
    # "unmounts previous effect"
    log: list[str] = []

    def App(*, step: int) -> object:
        def eff() -> object:
            log.append(f"mount:{step}")

            def cleanup() -> None:
                log.append(f"unmount:{step}")

            return cleanup

        use_effect(eff, (step,))
        return create_element("span", {"children": [str(step)]})

    set_act_environment_enabled(True)
    root = create_noop_root()
    try:
        with act(flush=root.flush):
            root.render(create_element(App, {"step": 1}))
        with act(flush=root.flush):
            root.render(create_element(App, {"step": 2}))
    finally:
        set_act_environment_enabled(False)

    assert log == ["mount:1", "unmount:1", "mount:2"]


def test_usestate_does_not_warn_on_set_after_unmount() -> None:
    # Upstream: ReactHooksWithNoopRenderer-test.js
    # "does not warn on set after unmount"
    set_v: list[object] = [None]

    def App() -> object:
        _, s = use_state(0)
        set_v[0] = s
        return create_element("span", {"children": ["ok"]})

    set_act_environment_enabled(True)
    root = create_noop_root()
    try:
        with act(flush=root.flush):
            root.render(create_element(App, {}))
        with act(flush=root.flush):
            root.render(None)
        with WarningCapture() as wc:
            set_v[0](1)  # type: ignore[misc]
        assert not wc.messages
    finally:
        set_act_environment_enabled(False)

