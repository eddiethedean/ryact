from __future__ import annotations

from typing import Any

from ryact import create_element
from ryact.concurrent import Thenable
from ryact.hooks import use_state
from ryact.use import use
from ryact_testkit import WarningCapture, create_noop_root


def test_warn_if_async_client_component_calls_hook_use() -> None:
    # Upstream: ReactUse-test.js
    # "warn if async client component calls a hook (e.g. use)"
    root = create_noop_root()
    t = Thenable()
    t.resolve("ok")

    async def App() -> Any:
        # Calling a hook from an async component should warn.
        return create_element("span", {"text": str(use(t))})

    with WarningCapture() as wc:
        root.render(create_element(App))
    wc.assert_any("Async generator components are not supported")


def test_warn_if_async_client_component_calls_hook_use_state_non_sync_update() -> None:
    # Upstream: ReactUse-test.js
    # "warn if async client component calls a hook (e.g. useState) during a non-sync update"
    #
    root = create_noop_root()

    async def App() -> Any:
        v, _set_v = use_state(0)
        return create_element("span", {"text": str(v)})

    with WarningCapture() as wc:
        root.render(create_element(App))
    wc.assert_any("Async generator components are not supported")
