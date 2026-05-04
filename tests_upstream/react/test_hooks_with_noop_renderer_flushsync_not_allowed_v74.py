from __future__ import annotations

from typing import Any

import pytest
from ryact import create_element, use_effect
from ryact_testkit import act, create_noop_root, set_act_environment_enabled


@pytest.mark.asyncio
async def test_flushsync_is_not_allowed() -> None:
    # Upstream: ReactHooksWithNoopRenderer-test.js
    # "flushSync is not allowed"
    root = create_noop_root()
    set_act_environment_enabled(True)
    try:

        def App() -> Any:
            def eff() -> Any:
                # Upstream throws if flushSync is called while React is flushing work.
                root.flush_sync(lambda: None)
                return None

            use_effect(eff, ())
            return create_element("span", {"text": "ok"})

        with pytest.raises(RuntimeError, match="flush_sync is not allowed"):
            with act(flush=root.flush):
                root.render(create_element(App))
    finally:
        set_act_environment_enabled(False)
