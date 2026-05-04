from __future__ import annotations

import asyncio

from ryact_testkit import WarningCapture, act_async, act_call, set_act_environment_enabled


def test_return_value_async_callback_nested() -> None:
    # Upstream: ReactIsomorphicAct-test.js
    # "return value – async callback, nested"
    set_act_environment_enabled(True)

    async def inner() -> str:
        await asyncio.sleep(0)
        return "inner"

    async def outer() -> str:
        # Nested call inside an event loop should work.
        out = await act_async(inner)  # type: ignore[func-returns-value]
        assert out == "inner"
        return "outer"

    assert act_call(lambda: asyncio.run(outer())) == "outer"


def test_warns_if_a_promise_is_used_in_a_non_awaited_act_scope() -> None:
    # Upstream: ReactIsomorphicAct-test.js
    # "warns if a promise is used in a non-awaited `act` scope"
    set_act_environment_enabled(True)

    async def cb() -> None:
        await asyncio.sleep(0)

    with WarningCapture() as cap:
        act_call(lambda: cb())

    cap.assert_any("await")
