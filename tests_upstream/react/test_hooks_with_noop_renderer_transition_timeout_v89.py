from __future__ import annotations

from typing import Any

import pytest
from ryact import create_element, use_state, use_transition
from ryact_testkit import act, create_noop_root, set_act_environment_enabled


@pytest.mark.asyncio
async def test_delays_showing_loading_state_until_after_timeout() -> None:
    # Upstream: ReactHooksWithNoopRenderer-test.js
    # "delays showing loading state until after timeout"
    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        setters: dict[str, Any] = {}

        def App() -> Any:
            pending, start = use_transition()
            v, set_v = use_state(0)
            setters["start"] = start
            setters["set_v"] = set_v
            return create_element("span", {"text": "loading" if pending else str(v)})

        with act(flush=root.flush):
            root.render(create_element(App))
        snap0 = root.get_children_snapshot()
        assert isinstance(snap0, dict)
        assert snap0["props"]["text"] == "0"

        setters["start"](lambda: setters["set_v"](1))  # type: ignore[misc]
        root.flush()
        # Pending should not flip immediately for a transition.
        snap1 = root.get_children_snapshot()
        assert isinstance(snap1, dict)
        assert snap1["props"]["text"] in ("0", "1")
    finally:
        set_act_environment_enabled(False)
