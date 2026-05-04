from __future__ import annotations

from typing import Any

import pytest
from ryact import create_element
from ryact.concurrent import Suspend, Thenable, suspense
from ryact_testkit import act, create_noop_root, set_act_environment_enabled


@pytest.mark.asyncio
async def test_does_not_infinite_loop_if_already_fulfilled_thenable_is_thrown() -> None:
    # Upstream: ReactUse-test.js
    # "does not infinite loop if already fulfilled thenable is thrown"
    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        t = Thenable()
        t.resolve("ok")

        def Child() -> Any:
            # Simulate an internal throw of a thenable that already fulfilled.
            raise Suspend(t)

        def App() -> Any:
            return suspense(
                fallback=create_element("span", {"text": "loading"}),
                children=create_element(Child),
            )

        with act(flush=root.flush):
            root.render(create_element(App))

        # Should not get stuck showing fallback / repeatedly rescheduling.
        snap = root.get_children_snapshot()
        assert snap is None or (isinstance(snap, dict) and snap.get("props", {}).get("text") != "loading")
    finally:
        set_act_environment_enabled(False)
