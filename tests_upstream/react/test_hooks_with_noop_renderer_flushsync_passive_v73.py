from __future__ import annotations

from typing import Any

import pytest

from ryact import create_element, use_effect, use_state
from ryact_testkit import act, create_noop_root, set_act_environment_enabled


@pytest.mark.asyncio
async def test_does_not_flush_non_discrete_passive_effects_when_flushing_sync() -> None:
    # Upstream: ReactHooksWithNoopRenderer-test.js
    # "does not flush non-discrete passive effects when flushing sync"
    log: list[str] = []
    setter: list[Any] = [None]

    def App() -> Any:
        v, set_v = use_state(0)
        setter[0] = set_v

        def eff() -> Any:
            log.append(f"passive {v}")
            return None

        use_effect(eff, (v,))
        return create_element("span", {"text": f"ok {v}"})

    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        with act(flush=root.flush):
            root.render(create_element(App))
        # Passive ran on initial mount.
        assert log == ["passive 0"]

        log.clear()
        root.flush_sync(lambda: setter[0](1))  # type: ignore[misc]
        # flushSync should commit the update, but not flush its passive effects.
        assert log == []

        root.flush()
        assert log == ["passive 1"]
    finally:
        set_act_environment_enabled(False)

