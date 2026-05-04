from __future__ import annotations

from typing import Any

import pytest
from ryact import create_element, use_effect, use_state
from ryact_testkit import act, create_noop_root, set_act_environment_enabled
from ryact_testkit.warnings import WarningCapture


@pytest.mark.asyncio
async def test_does_not_warn_unmounted_updates_with_no_pending_passive_unmounts() -> None:
    # Upstream: ReactHooksWithNoopRenderer-test.js
    # "does not warn about state updates for unmounted components with no pending passive unmounts"
    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        setter: list[Any] = [None]

        def Child() -> Any:
            v, set_v = use_state(0)
            setter[0] = set_v
            return create_element("span", {"text": str(v)})

        with act(flush=root.flush):
            root.render(create_element(Child))
        # Unmount completely.
        with act(flush=root.flush):
            root.render(None)

        with WarningCapture() as wc:
            setter[0](1)  # type: ignore[misc]
            root.flush()
        assert wc.messages == []
    finally:
        set_act_environment_enabled(False)


@pytest.mark.asyncio
async def test_does_not_warn_unmounted_updates_with_pending_passive_unmounts() -> None:
    # Upstream: ReactHooksWithNoopRenderer-test.js
    # "does not warn about state updates for unmounted components with pending passive unmounts"
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

        # Unmount, but do not flush pending passives yet (noop defers passive unmount destroys).
        with act(flush=root.flush):
            root.render(None)

        with WarningCapture() as wc:
            setter[0](1)  # type: ignore[misc]
            root.flush()
        assert wc.messages == []
    finally:
        set_act_environment_enabled(False)


@pytest.mark.asyncio
async def test_does_not_warn_unmounted_updates_with_pending_passive_unmounts_for_alternates() -> None:
    # Upstream: ReactHooksWithNoopRenderer-test.js
    # "does not warn about state updates for unmounted components with pending passive unmounts for alternates"
    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        setters: dict[str, Any] = {}

        def Child(*, id: str) -> Any:
            v, set_v = use_state(0)
            setters[id] = set_v

            def eff() -> Any:
                def destroy() -> None:
                    return None

                return destroy

            use_effect(eff, ())
            return create_element("span", {"text": str(v)})

        with act(flush=root.flush):
            root.render(create_element("div", {"children": [create_element(Child, {"id": "a"})]}))

        # Replace child with a different keyed child; old fiber becomes an alternate/unmounted.
        with act(flush=root.flush):
            root.render(create_element("div", {"children": [create_element(Child, {"id": "b"})]}))

        with WarningCapture() as wc:
            setters["a"](1)  # type: ignore[misc]
            root.flush()
        assert wc.messages == []
    finally:
        set_act_environment_enabled(False)
