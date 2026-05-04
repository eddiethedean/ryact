from __future__ import annotations

from typing import Any

import pytest

from ryact import create_element, use_effect, use_state
from ryact_testkit import act, create_noop_root, set_act_environment_enabled
from ryact_testkit.warnings import WarningCapture


@pytest.mark.asyncio
async def test_does_not_show_warning_when_updating_child_state_from_passive_unmount() -> None:
    # Upstream: ReactHooksWithNoopRenderer-test.js
    # "does not show a warning when a component updates a child state from within passive unmount function"
    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        child_setter: list[Any] = [None]

        def Child() -> Any:
            v, set_v = use_state(0)
            child_setter[0] = set_v
            return create_element("span", {"text": f"child {v}"})

        def Parent() -> Any:
            show, set_show = use_state(True)

            def eff() -> Any:
                def destroy() -> None:
                    # Update unmounted child from its passive unmount cleanup.
                    child_setter[0](1)  # type: ignore[misc]

                # Unmount child so it has a passive destroy.
                set_show(False)
                return destroy

            use_effect(eff, ())
            return create_element("div", {"children": [create_element(Child) if show else None]})

        with WarningCapture() as wc:
            with act(flush=root.flush):
                root.render(create_element(Parent))
            # Passive destroy should be deferred, and when it runs it should not warn.
            root.flush()
        assert wc.messages == []
    finally:
        set_act_environment_enabled(False)


@pytest.mark.asyncio
async def test_does_not_show_warning_when_updating_parent_state_from_passive_unmount() -> None:
    # Upstream: ReactHooksWithNoopRenderer-test.js
    # "does not show a warning when a component updates a parents state from within passive unmount function"
    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        parent_setter: list[Any] = [None]

        def Parent() -> Any:
            v, set_v = use_state(0)
            parent_setter[0] = set_v
            show, set_show = use_state(True)

            def eff() -> Any:
                def destroy() -> None:
                    parent_setter[0](v + 1)  # type: ignore[misc]

                set_show(False)
                return destroy

            use_effect(eff, ())
            return create_element("div", {"children": [create_element("span", {"text": str(v)})]})

        with WarningCapture() as wc:
            with act(flush=root.flush):
                root.render(create_element(Parent))
            root.flush()
        assert wc.messages == []
    finally:
        set_act_environment_enabled(False)


@pytest.mark.asyncio
async def test_does_not_show_warning_when_updating_own_state_from_passive_unmount() -> None:
    # Upstream: ReactHooksWithNoopRenderer-test.js
    # "does not show a warning when a component updates its own state from within passive unmount function"
    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        setter: list[Any] = [None]

        def App() -> Any:
            v, set_v = use_state(0)
            setter[0] = set_v
            show, set_show = use_state(True)

            def eff() -> Any:
                def destroy() -> None:
                    setter[0](v + 1)  # type: ignore[misc]

                set_show(False)
                return destroy

            use_effect(eff, ())
            return create_element("div", {"children": [create_element("span", {"text": str(v)})]})

        with WarningCapture() as wc:
            with act(flush=root.flush):
                root.render(create_element(App))
            root.flush()
        assert wc.messages == []
    finally:
        set_act_environment_enabled(False)

