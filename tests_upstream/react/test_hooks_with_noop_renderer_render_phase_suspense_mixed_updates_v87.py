from __future__ import annotations

from typing import Any

import pytest
from ryact import create_element, use_state
from ryact.concurrent import Thenable, suspense
from ryact.use import use
from ryact_testkit import act, create_noop_root, set_act_environment_enabled


@pytest.mark.asyncio
async def test_discards_render_phase_updates_if_something_suspends_but_not_other_updates() -> None:
    # Upstream: ReactHooksWithNoopRenderer-test.js
    # "discards render phase updates if something suspends, but not other updates in the same component"
    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        t = Thenable()
        did_render_update: list[bool] = [False]
        parent_setter: list[Any] = [None]

        def Child(*, value: int) -> Any:
            v, set_v = use_state(0)
            if v == 0 and not did_render_update[0]:
                did_render_update[0] = True
                set_v(1)  # render-phase update (should be discarded by suspension)
            use(t)
            return create_element("span", {"text": f"v={v} prop={value}"})

        def Parent() -> Any:
            value, set_value = use_state(0)
            parent_setter[0] = set_value
            return suspense(
                fallback=create_element("span", {"text": "loading"}),
                children=create_element(Child, {"value": value}),
            )

        with act(flush=root.flush):
            root.render(create_element(Parent))
        snap0 = root.get_children_snapshot()
        assert isinstance(snap0, dict)
        assert snap0["props"]["text"] == "loading"

        # Queue a normal (non-render-phase) update above the suspended subtree.
        assert parent_setter[0] is not None
        parent_setter[0](2)  # type: ignore[misc]
        root.flush()
        snap_mid = root.get_children_snapshot()
        assert isinstance(snap_mid, dict)
        assert snap_mid["props"]["text"] == "loading"

        with act(flush=root.flush):
            t.resolve("ok")
        snap1 = root.get_children_snapshot()
        assert isinstance(snap1, dict)
        assert snap1["props"]["text"] == "v=0 prop=2"
    finally:
        set_act_environment_enabled(False)
