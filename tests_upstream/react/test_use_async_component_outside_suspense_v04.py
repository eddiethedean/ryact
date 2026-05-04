from __future__ import annotations

from typing import Any

import pytest
from ryact import create_element
from ryact_testkit import WarningCapture, act, create_noop_root, set_act_environment_enabled


@pytest.mark.asyncio
async def test_async_component_outside_suspense_crashes_microtask() -> None:
    # Upstream: ReactUse-test.js
    # "an async component outside of a Suspense boundary crashes with an error (resolves in microtask)"
    async def App() -> Any:  # type: ignore[func-returns-value]
        return create_element("span", {"text": "hi"})

    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        with WarningCapture() as wc, act(flush=root.flush):
            root.render(create_element(App))
        wc.assert_any("Async generator components are not supported")
        assert root.get_children_snapshot() is None
    finally:
        set_act_environment_enabled(False)


@pytest.mark.asyncio
async def test_async_component_outside_suspense_crashes_macrotask() -> None:
    # Upstream: ReactUse-test.js
    # "an async component outside of a Suspense boundary crashes with an error (resolves in macrotask)"
    async def App() -> Any:  # type: ignore[func-returns-value]
        return create_element("span", {"text": "hi"})

    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        with WarningCapture() as wc, act(flush=root.flush):
            root.render(create_element(App))
        wc.assert_any("Async generator components are not supported")
        assert root.get_children_snapshot() is None
    finally:
        set_act_environment_enabled(False)
