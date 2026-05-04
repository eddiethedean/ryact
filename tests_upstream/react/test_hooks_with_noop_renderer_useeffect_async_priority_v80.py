from __future__ import annotations

from typing import Any

import pytest

from ryact import create_element, use_effect, use_state
from ryact_testkit import act, create_noop_root, set_act_environment_enabled


@pytest.mark.asyncio
async def test_updates_have_async_priority() -> None:
    # Upstream: ReactHooksWithNoopRenderer-test.js
    # "updates have async priority"
    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        def App() -> Any:
            v, set_v = use_state(0)

            def eff() -> Any:
                set_v(1)
                return None

            use_effect(eff, ())
            return create_element("span", {"text": str(v)})

        with act():
            root.render(create_element(App))

        # Passive effect scheduled an update, but it should not have committed yet.
        snap0 = root.get_children_snapshot()
        assert isinstance(snap0, dict)
        assert snap0["props"]["text"] == "0"

        root.flush()
        snap1 = root.get_children_snapshot()
        assert isinstance(snap1, dict)
        assert snap1["props"]["text"] == "1"
    finally:
        set_act_environment_enabled(False)


@pytest.mark.asyncio
async def test_updates_have_async_priority_even_if_effects_flushed_early() -> None:
    # Upstream: ReactHooksWithNoopRenderer-test.js
    # "updates have async priority even if effects are flushed early"
    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        rr = root._reconciler_root

        def App() -> Any:
            v, set_v = use_state(0)

            def eff() -> Any:
                set_v(1)
                return None

            use_effect(eff, ())
            return create_element("span", {"text": str(v)})

        # First commit: defer passives so the effect is queued into pending passives.
        rr._defer_passive_effects = True  # type: ignore[attr-defined]
        with act():
            root.render(create_element(App))
        snap0 = root.get_children_snapshot()
        assert isinstance(snap0, dict)
        assert snap0["props"]["text"] == "0"

        # Second commit: allow draining pending passives before new layout effects.
        rr._defer_passive_effects = False  # type: ignore[attr-defined]
        with act():
            root.render(create_element(App))

        # The drained passive effect scheduled an update, but it should not have committed
        # during the same flush that drained it.
        snap1 = root.get_children_snapshot()
        assert isinstance(snap1, dict)
        assert snap1["props"]["text"] == "0"

        root.flush()
        snap2 = root.get_children_snapshot()
        assert isinstance(snap2, dict)
        assert snap2["props"]["text"] == "1"
    finally:
        set_act_environment_enabled(False)

