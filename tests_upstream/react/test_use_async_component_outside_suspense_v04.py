from __future__ import annotations

from typing import Any

import pytest
from ryact import create_element
from ryact_testkit import act, create_noop_root, set_act_environment_enabled


@pytest.mark.asyncio
async def test_async_component_outside_suspense_crashes_microtask() -> None:
    # Upstream: ReactUse-test.js
    # "an async component outside of a Suspense boundary crashes with an error (resolves in microtask)"
    async def App() -> Any:  # type: ignore[func-returns-value]
        return create_element("span", {"text": "hi"})

    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        with pytest.raises(RuntimeError, match="Async component functions are not supported"):
            with act(flush=root.flush):
                root.render(create_element(App))
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
        with pytest.raises(RuntimeError, match="Async component functions are not supported"):
            with act(flush=root.flush):
                root.render(create_element(App))
    finally:
        set_act_environment_enabled(False)
