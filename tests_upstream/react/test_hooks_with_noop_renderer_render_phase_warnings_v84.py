from __future__ import annotations

from typing import Any

import pytest
from ryact import create_element, use_state, use_transition
from ryact_testkit import act, create_noop_root, set_act_environment_enabled
from ryact_testkit.warnings import WarningCapture


@pytest.mark.asyncio
async def test_warns_about_render_phase_update_on_a_different_component() -> None:
    # Upstream: ReactHooksWithNoopRenderer-test.js
    # "warns about render phase update on a different component"
    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        setters: dict[str, Any] = {}

        def A() -> Any:
            v, set_v = use_state(0)
            setters["A"] = set_v
            return create_element("span", {"text": f"A {v}"})

        def B() -> Any:
            v, set_v = use_state(0)
            setters["B"] = set_v
            # Trigger an update to A during B's render.
            if setters.get("A") is not None and v == 0:
                setters["A"](1)  # type: ignore[misc]
            return create_element("span", {"text": f"B {v}"})

        with WarningCapture() as wc, act(flush=root.flush):
            root.render(
                create_element("div", {"children": [create_element(A), create_element(B)]})
            )
        wc.assert_any("Cannot update a component while rendering a different component.")
    finally:
        set_act_environment_enabled(False)


@pytest.mark.asyncio
async def test_calling_starttransition_inside_render_phase_does_not_crash() -> None:
    # Upstream: ReactHooksWithNoopRenderer-test.js
    # "calling startTransition inside render phase"
    root = create_noop_root()
    set_act_environment_enabled(True)
    try:

        def App() -> Any:
            _pending, start = use_transition()
            v, set_v = use_state(0)
            if v == 0:
                start(lambda: set_v(1))
            return create_element("span", {"text": str(v)})

        with WarningCapture() as wc, act(flush=root.flush):
            root.render(create_element(App))
        wc.assert_any("calling startTransition inside render phase")
        snap = root.get_children_snapshot()
        assert isinstance(snap, dict)
        assert snap["props"]["text"] == "1"
    finally:
        set_act_environment_enabled(False)
