from __future__ import annotations

from typing import Any

import pytest
from ryact import create_element, use_effect, use_state
from ryact_testkit import act, create_noop_root, set_act_environment_enabled


@pytest.mark.asyncio
async def test_defers_passive_effect_destroy_functions_during_unmount() -> None:
    # Upstream: ReactHooksWithNoopRenderer-test.js
    # "defers passive effect destroy functions during unmount"
    log: list[str] = []

    def Child() -> Any:
        def eff() -> Any:
            log.append("create")

            def destroy() -> None:
                log.append("destroy")

            return destroy

        use_effect(eff, ())
        return create_element("span", {"text": "child"})

    def App() -> Any:
        show, set_show = use_state(True)

        def eff() -> Any:
            # Unmount child during passive create; destroy should be deferred.
            set_show(False)
            log.append("parent effect")
            return None

        use_effect(eff, ())
        return create_element("div", {"children": [create_element(Child) if show else None]})

    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        with act(flush=root.flush):
            root.render(create_element(App))

        # We should have created the child's effect, then run parent's effect that unmounts it.
        assert "create" in log
        assert "parent effect" in log
        # Child destroy is deferred to a later passive flush, not run during the unmount commit.
        assert "destroy" not in log

        root.flush()
        assert "destroy" in log
    finally:
        set_act_environment_enabled(False)
