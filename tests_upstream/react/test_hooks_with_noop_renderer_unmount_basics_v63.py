from __future__ import annotations

from typing import Any

from ryact import create_element, use_effect, use_state
from ryact_testkit import act, create_noop_root, set_act_environment_enabled


def test_unmount_effects() -> None:
    # Upstream: ReactHooksWithNoopRenderer-test.js
    # "unmount effects"
    log: list[str] = []

    def App() -> Any:
        def eff() -> Any:
            log.append("mount")

            def cleanup() -> None:
                log.append("unmount")

            return cleanup

        use_effect(eff, ())
        return create_element("span", {"text": "hi"})

    set_act_environment_enabled(True)
    root = create_noop_root()
    try:
        with act(flush=root.flush):
            root.render(create_element(App))
        with act(flush=root.flush):
            root.render(None)
    finally:
        set_act_environment_enabled(False)

    assert log == ["mount", "unmount"]


def test_unmount_state() -> None:
    # Upstream: ReactHooksWithNoopRenderer-test.js
    # "unmount state"
    set_v: list[Any] = [None]

    def App() -> Any:
        v, s = use_state(0)
        set_v[0] = s
        return create_element("span", {"text": str(v)})

    set_act_environment_enabled(True)
    root = create_noop_root()
    try:
        with act(flush=root.flush):
            root.render(create_element(App))
        with act(flush=root.flush):
            root.render(None)
        # Post-unmount setState should be a no-op/no-warn in our harness.
        set_v[0](1)
        root.flush()
    finally:
        set_act_environment_enabled(False)

    assert root.get_children_snapshot() is None
