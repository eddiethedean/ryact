from __future__ import annotations

from typing import Any

import pytest
from ryact import create_element, use_state, use_transition
from ryact_testkit import act, create_noop_root, set_act_environment_enabled
from schedulyr import Scheduler


@pytest.mark.asyncio
async def test_regression_render_phase_updates_do_not_drop_lower_priority_work() -> None:
    # Upstream: ReactHooksWithNoopRenderer-test.js
    # "regression: render phase updates cause lower pri work to be dropped"
    root = create_noop_root(scheduler=Scheduler())
    set_act_environment_enabled(True)
    try:
        setters: dict[str, Any] = {}

        def App() -> Any:
            _pending, start = use_transition()
            v, set_v = use_state(0)
            setters["set_v"] = set_v
            setters["start"] = start
            return create_element("span", {"text": str(v)})

        with act(flush=root.flush):
            root.render(create_element(App))

        # Queue a default update, then a transition-lane update (lower priority).
        # The transition work must not be dropped by concurrent-root coalescing.
        setters["set_v"](1)  # type: ignore[misc]
        setters["start"](lambda: setters["set_v"](2))  # type: ignore[misc]

        # First flush should commit the higher priority update.
        root.flush()
        snap1 = root.get_children_snapshot()
        assert isinstance(snap1, dict)
        assert snap1["props"]["text"] == "1"
        assert root._reconciler_root.pending_updates
        # Ensure the state hook still has a deferred (transition) pending update.
        cur = root._reconciler_root.current
        assert cur is not None
        f = cur.child
        while f is not None and getattr(f, "type", None) is not App:
            f = getattr(f, "child", None) or getattr(f, "sibling", None)
        assert f is not None
        hooks = getattr(f, "hooks", None) or []
        assert any(getattr(h, "pending", None) for h in hooks)

        # The lower priority transition work should still eventually apply (not dropped).
        for _ in range(5):
            root.flush()
            snap2 = root.get_children_snapshot()
            assert isinstance(snap2, dict)
            if snap2["props"]["text"] == "2":
                break
        assert snap2["props"]["text"] == "2"
    finally:
        set_act_environment_enabled(False)
