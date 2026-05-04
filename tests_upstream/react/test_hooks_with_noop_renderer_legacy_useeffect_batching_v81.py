from __future__ import annotations

from typing import Any

import pytest
from ryact import create_element, use_effect, use_state
from ryact_testkit import act, create_noop_root, set_act_environment_enabled


@pytest.mark.asyncio
async def test_in_legacy_mode_useeffect_deferred_updates_finish_synchronously() -> None:
    # Upstream: ReactHooksWithNoopRenderer-test.js
    # "in legacy mode, useEffect is deferred and updates finish synchronously (in a single batch)"
    root = create_noop_root(legacy=True)
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

        snap0 = root.get_children_snapshot()
        assert isinstance(snap0, dict)
        assert snap0["props"]["text"] == "0"

        # In legacy mode, once passive effects flush, any updates they schedule finish
        # synchronously in the same batch.
        root.flush()
        snap1 = root.get_children_snapshot()
        assert isinstance(snap1, dict)
        assert snap1["props"]["text"] == "1"
    finally:
        set_act_environment_enabled(False)
