from __future__ import annotations

from typing import Any

import pytest

from ryact import create_element, use_effect, use_state
from ryact_testkit import act, create_noop_root, set_act_environment_enabled
from ryact_testkit.warnings import WarningCapture


@pytest.mark.asyncio
async def test_does_not_warn_if_pending_passive_unmount_effects_not_for_current_fiber() -> None:
    # Upstream: ReactHooksWithNoopRenderer-test.js
    # "does not warn if there are pending passive unmount effects but not for the current fiber"
    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        b_setter: list[Any] = [None]

        def A() -> Any:
            def eff() -> Any:
                def destroy() -> None:
                    return None

                return destroy

            use_effect(eff, ())
            return create_element("span", {"text": "A"})

        def B() -> Any:
            v, set_v = use_state(0)
            b_setter[0] = set_v
            return create_element("span", {"text": f"B {v}"})

        with act(flush=root.flush):
            root.render(
                create_element(
                    "div",
                    {
                        "children": [
                            create_element(A, {"key": "a"}),
                            create_element(B, {"key": "b"}),
                        ]
                    },
                )
            )

        # Unmount both. A has a pending passive unmount cleanup; B does not.
        with act(flush=root.flush):
            root.render(None)

        with WarningCapture() as wc:
            b_setter[0](1)  # type: ignore[misc]
            root.flush()
        assert wc.messages == []
    finally:
        set_act_environment_enabled(False)


@pytest.mark.asyncio
async def test_does_not_warn_if_updates_after_pending_passive_unmount_flushed() -> None:
    # Upstream: ReactHooksWithNoopRenderer-test.js
    # "does not warn if there are updates after pending passive unmount effects have been flushed"
    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        setter: list[Any] = [None]

        def Child() -> Any:
            v, set_v = use_state(0)
            setter[0] = set_v

            def eff() -> Any:
                def destroy() -> None:
                    return None

                return destroy

            use_effect(eff, ())
            return create_element("span", {"text": str(v)})

        with act(flush=root.flush):
            root.render(create_element(Child))

        # Unmount to enqueue a pending passive unmount cleanup.
        with act(flush=root.flush):
            root.render(None)

        # Flush pending passive unmount effects.
        root.flush()

        with WarningCapture() as wc:
            setter[0](1)  # type: ignore[misc]
            root.flush()
        assert wc.messages == []
    finally:
        set_act_environment_enabled(False)

