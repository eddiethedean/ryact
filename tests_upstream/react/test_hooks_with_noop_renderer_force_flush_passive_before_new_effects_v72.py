from __future__ import annotations

from typing import Any

from ryact import create_element, use_effect, use_insertion_effect, use_layout_effect, use_state
from ryact_testkit import act, create_noop_root, set_act_environment_enabled


def test_force_flushes_passive_effects_before_firing_new_insertion_effects() -> None:
    # Upstream: ReactHooksWithNoopRenderer-test.js
    # "force flushes passive effects before firing new insertion effects"
    log: list[str] = []
    root = create_noop_root()
    # Test harness knob: defer passives so they remain pending across commits.
    root._reconciler_root._defer_passive_effects = True  # type: ignore[attr-defined]

    def App(*, step: int) -> Any:
        def passive() -> Any:
            log.append(f"passive:{step}")
            return None

        use_effect(passive, (step,))

        def ins() -> Any:
            log.append(f"insertion:{step}")
            return None

        use_insertion_effect(ins, (step,))
        return create_element("span", {"text": str(step)})

    set_act_environment_enabled(True)
    try:
        with act(flush=root.flush):
            root.render(create_element(App, {"step": 0}))
        assert log == ["insertion:0"]

        with act(flush=root.flush):
            root.render(create_element(App, {"step": 1}))
        # Pending passive from step=0 must flush before new insertion step=1.
        assert log[1:3] == ["passive:0", "insertion:1"]
    finally:
        set_act_environment_enabled(False)


def test_force_flushes_passive_effects_before_firing_new_layout_effects() -> None:
    # Upstream: ReactHooksWithNoopRenderer-test.js
    # "force flushes passive effects before firing new layout effects"
    log: list[str] = []
    root = create_noop_root()
    root._reconciler_root._defer_passive_effects = True  # type: ignore[attr-defined]

    def App(*, step: int) -> Any:
        def passive() -> Any:
            log.append(f"passive:{step}")
            return None

        use_effect(passive, (step,))

        def lay() -> Any:
            log.append(f"layout:{step}")
            return None

        use_layout_effect(lay, (step,))
        return create_element("span", {"text": str(step)})

    set_act_environment_enabled(True)
    try:
        with act(flush=root.flush):
            root.render(create_element(App, {"step": 0}))
        assert log == ["layout:0"]

        with act(flush=root.flush):
            root.render(create_element(App, {"step": 1}))
        # Pending passive from step=0 must flush before new layout step=1.
        assert log[1:3] == ["passive:0", "layout:1"]
    finally:
        set_act_environment_enabled(False)

