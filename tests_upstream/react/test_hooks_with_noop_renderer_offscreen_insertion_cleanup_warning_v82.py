from __future__ import annotations

from typing import Any

import pytest

from ryact import create_element, use_insertion_effect, use_state
from ryact_testkit import act, create_noop_root, set_act_environment_enabled
from ryact_testkit.warnings import WarningCapture


@pytest.mark.asyncio
async def test_warns_when_setstate_called_from_offscreen_deleted_insertion_effect_cleanup() -> None:
    # Upstream: ReactHooksWithNoopRenderer-test.js
    # "warns when setState is called from offscreen deleted insertion effect cleanup"
    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        log: list[str] = []

        def App() -> Any:
            _v, set_v = use_state(0)

            def ins() -> Any:
                log.append("create")

                def cleanup() -> None:
                    log.append("cleanup")
                    # This should warn and be ignored.
                    set_v(1)

                return cleanup

            use_insertion_effect(ins, ())
            return create_element("span", {"text": "child"})

        with act(flush=root.flush):
            root.render(create_element(App))
        assert log == ["create"]
        log.clear()
        with WarningCapture() as wc:
            with act(flush=root.flush):
                root.render(None)
        assert log == ["cleanup"]
        wc.assert_any("Cannot update state from within an insertion effect")
    finally:
        set_act_environment_enabled(False)

