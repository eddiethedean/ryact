from __future__ import annotations

from typing import Any

import pytest

from ryact import create_element, use_state
from ryact.concurrent import Thenable, suspense
from ryact.use import use
from ryact_testkit import act, create_noop_root, set_act_environment_enabled


@pytest.mark.asyncio
async def test_discards_render_phase_updates_if_something_suspends() -> None:
    # Upstream: ReactHooksWithNoopRenderer-test.js
    # "discards render phase updates if something suspends"
    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        t = Thenable()
        did_render_update: list[bool] = [False]

        def Child() -> Any:
            v, set_v = use_state(0)
            # Render-phase update should be discarded if this render suspends.
            if v == 0 and not did_render_update[0]:
                did_render_update[0] = True
                set_v(1)  # render-phase update
            # Suspend on first render attempt.
            use(t)
            return create_element("span", {"text": str(v)})

        def App() -> Any:
            return suspense(fallback=create_element("span", {"text": "loading"}), children=create_element(Child))

        with act(flush=root.flush):
            root.render(create_element(App))
        snap0 = root.get_children_snapshot()
        assert isinstance(snap0, dict)
        assert snap0["props"]["text"] == "loading"

        # Resolve and flush again; render-phase update should have been discarded.
        with act(flush=root.flush):
            t.resolve("ok")
        snap1 = root.get_children_snapshot()
        assert isinstance(snap1, dict)
        assert snap1["props"]["text"] == "0"
    finally:
        set_act_environment_enabled(False)

