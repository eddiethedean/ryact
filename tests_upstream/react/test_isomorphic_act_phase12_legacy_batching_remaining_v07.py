from __future__ import annotations

import asyncio
from typing import Any

from ryact import create_element, use
from ryact.concurrent import Thenable, suspense
from ryact_testkit import (
    WarningCapture,
    act_async,
    act_call,
    create_noop_root,
    set_act_environment_enabled,
)


def _span(value: str) -> Any:
    return create_element("span", {"text": value})


def _legacy_act_call(root, fn) -> Any:
    # Legacy-mode act batches updates until the end of the scope.
    return act_call(lambda: root.batched_updates(fn), flush=root.flush, drain_microtasks=2)


def test_does_not_warn_when_suspending_via_legacy_throw_api_in_non_awaited_act_scope() -> None:
    # Upstream: ReactIsomorphicAct-test.js
    # "does not warn when suspending via legacy `throw` API  in non-awaited `act` scope"
    set_act_environment_enabled(True)
    root = create_noop_root(legacy=True)
    t = Thenable()

    def Child() -> Any:
        use(t)
        return _span("done")

    def App() -> Any:
        return suspense(fallback=_span("fb"), children=create_element(Child))

    with WarningCapture() as cap:
        _legacy_act_call(root, lambda: root.render(create_element(App)))
    assert cap.messages == []
    assert root.container.last_committed["props"]["text"] == "fb"


def test_in_legacy_mode_updates_are_batched() -> None:
    # Upstream: ReactIsomorphicAct-test.js
    # "in legacy mode, updates are batched"
    set_act_environment_enabled(True)
    root = create_noop_root(legacy=True)

    def render(value: str) -> None:
        root.render(_span(value))

    _legacy_act_call(root, lambda: (render("A"), render("B")))
    assert root.container.last_committed["props"]["text"] == "B"


def test_in_legacy_mode_in_async_scope_updates_are_batched_until_first_await() -> None:
    # Upstream: ReactIsomorphicAct-test.js
    # "in legacy mode, in an async scope, updates are batched until the first `await`"
    set_act_environment_enabled(True)
    root = create_noop_root(legacy=True)

    async def cb() -> None:
        root.batched_updates(lambda: root.render(_span("A")))
        await asyncio.sleep(0)
        root.render(_span("B"))

    act_async(cb, flush=root.flush)
    assert root.container.last_committed["props"]["text"] == "B"


def test_in_legacy_mode_in_async_scope_updates_are_batched_until_first_await_regression_batchedupdates() -> (
    None
):
    # Upstream: ReactIsomorphicAct-test.js
    # "in legacy mode, in an async scope, updates are batched until the first `await` (regression test: batchedUpdates)"
    set_act_environment_enabled(True)
    root = create_noop_root(legacy=True)

    async def cb() -> None:
        root.batched_updates(lambda: root.render(_span("A")))
        await asyncio.sleep(0)
        root.batched_updates(lambda: root.render(_span("B")))

    act_async(cb, flush=root.flush)
    assert root.container.last_committed["props"]["text"] == "B"
