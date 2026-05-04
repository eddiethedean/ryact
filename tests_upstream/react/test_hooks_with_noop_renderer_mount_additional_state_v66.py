from __future__ import annotations

import pytest
from ryact import create_element, use_state
from ryact.hooks import HookError
from ryact_testkit import act, create_noop_root, set_act_environment_enabled


def test_mount_additional_state() -> None:
    # Upstream: ReactHooksWithNoopRenderer-test.js
    # "mount additional state"
    root = create_noop_root()

    def App(*, extra: bool) -> object:
        _a, _ = use_state(0)
        if extra:
            _b, _ = use_state(1)
        return create_element("span", {"text": "ok"})

    set_act_environment_enabled(True)
    try:
        with act(flush=root.flush):
            root.render(create_element(App, {"extra": False}))
        # Adding a hook on update should error (hook order/count must be stable).
        with pytest.raises(HookError, match="Rendered more hooks than during the previous render"):
            with act(flush=root.flush):
                root.render(create_element(App, {"extra": True}))
    finally:
        set_act_environment_enabled(False)
