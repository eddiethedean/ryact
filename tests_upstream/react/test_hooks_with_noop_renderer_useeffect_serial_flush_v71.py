from __future__ import annotations

from typing import Any

from ryact import create_element, use_effect
from ryact_testkit import act, create_noop_root, set_act_environment_enabled


def test_flushes_effects_serially_by_flushing_old_before_new() -> None:
    # Upstream: ReactHooksWithNoopRenderer-test.js
    # "flushes effects serially by flushing old effects before flushing new ones, if they haven't already fired"
    log: list[str] = []

    def App(*, step: int) -> Any:
        def eff() -> Any:
            log.append(f"create:{step}")

            def cleanup() -> None:
                log.append(f"destroy:{step}")

            return cleanup

        use_effect(eff, (step,))
        return create_element("span", {"text": str(step)})

    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        with act(flush=root.flush):
            root.render(create_element(App, {"step": 1}))
        with act(flush=root.flush):
            root.render(create_element(App, {"step": 2}))
    finally:
        set_act_environment_enabled(False)

    # Old destroy must flush before new create.
    assert log == ["create:1", "destroy:1", "create:2"]

