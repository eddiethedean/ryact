from __future__ import annotations

import asyncio
from typing import Any

from ryact import create_element, use_state
from ryact_testkit import act, act_async, create_noop_root, set_act_environment_enabled


def _span(value: str) -> Any:
    return create_element("span", {"text": value})


def test_return_value_async_callback() -> None:
    # Upstream: ReactIsomorphicAct-test.js
    # "return value – async callback"
    set_act_environment_enabled(True)

    async def cb() -> str:
        await asyncio.sleep(0)
        return "ok"

    assert act_async(cb) == "ok"


def test_unwraps_promises_by_yielding_to_microtasks_async_act_scope() -> None:
    # Upstream: ReactIsomorphicAct-test.js
    # "unwraps promises by yielding to microtasks (async act scope)"
    set_act_environment_enabled(True)
    root = create_noop_root()
    setter_ref: list[Any] = [None]

    def App() -> Any:
        value, set_value = use_state("A")
        setter_ref[0] = set_value
        return _span(str(value))

    with act(flush=root.flush):
        root.render(create_element(App))
    assert root.container.last_committed["props"]["text"] == "A"

    async def cb() -> None:
        loop = asyncio.get_running_loop()
        fut: asyncio.Future[None] = loop.create_future()

        def _microtask() -> None:
            set_value = setter_ref[0]
            set_value("B")
            fut.set_result(None)

        loop.call_soon(_microtask)
        await fut

    act_async(cb, flush=root.flush)
    assert root.container.last_committed["props"]["text"] == "B"
