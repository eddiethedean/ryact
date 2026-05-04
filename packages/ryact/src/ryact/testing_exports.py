"""Lazy re-exports of ``ryact-testkit`` helpers (optional dependency).

Installing ``ryact`` alone does not install ``ryact-testkit``. The workspace / dev
installs include both so ``from ryact import act`` works in translated tests.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any


def _testkit_act_module() -> Any:
    try:
        import ryact_testkit as m
    except ImportError as e:
        raise ImportError(
            "The testing helpers `act`, `act_call`, and `act_async` require the "
            "`ryact-testkit` package (workspace dev dependency)."
        ) from e
    return m


def act(flush: Callable[[], None] | None = None):
    """Mirror ``ryact_testkit.act.act`` (sync ``act`` scope)."""

    return _testkit_act_module().act(flush)


def act_call(
    callback: Callable[[], Any],
    *,
    flush: Callable[[], None] | None = None,
    drain_microtasks: int = 0,
) -> Any:
    return _testkit_act_module().act_call(callback, flush=flush, drain_microtasks=drain_microtasks)


def act_async(
    callback: Callable[[], Any] | Callable[[], Awaitable[Any]],
    *,
    flush: Callable[[], None] | None = None,
    max_microtasks: int = 50,
) -> Any:
    return _testkit_act_module().act_async(callback, flush=flush, max_microtasks=max_microtasks)


def set_act_environment_enabled(value: bool) -> None:
    _testkit_act_module().set_act_environment_enabled(value)
