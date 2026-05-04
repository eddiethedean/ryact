from __future__ import annotations

from typing import Any

import pytest
from ryact import Component, create_element
from ryact.concurrent import fragment, suspense_list
from ryact_testkit import act, create_noop_root, set_act_environment_enabled


@pytest.mark.asyncio
async def test_regression_suspenselist_causes_unmounts_to_be_dropped_on_deletion() -> None:
    # Upstream: ReactHooksWithNoopRenderer-test.js
    # "regression: SuspenseList causes unmounts to be dropped on deletion"
    log: list[str] = []

    class Child(Component):
        def componentWillUnmount(self) -> None:
            log.append("unmount")

        def render(self) -> Any:
            return create_element("span", {"text": "child"})

    def App(*, show: bool) -> Any:
        if not show:
            return None
        return suspense_list(
            reveal_order="forwards",
            tail="hidden",
            children=fragment(create_element(Child)),
        )

    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        with act(flush=root.flush):
            root.render(create_element(App, {"show": True}))
        log.clear()
        with act(flush=root.flush):
            root.render(create_element(App, {"show": False}))
        assert log == ["unmount"]
    finally:
        set_act_environment_enabled(False)
