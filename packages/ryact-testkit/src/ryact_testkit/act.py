from __future__ import annotations

from collections.abc import Callable, Generator
from contextlib import contextmanager
import asyncio
import inspect
from typing import Any, Awaitable

from ryact.act import (
    act_scope,
    is_act_environment_enabled,
    set_act_environment_enabled as _set_act_environment_enabled,
)

from .warnings import emit_warning


def set_act_environment_enabled(value: bool) -> None:
    _set_act_environment_enabled(value)


@contextmanager
def act(flush: Callable[[], None] | None = None) -> Generator[None, None, None]:
    """
    Minimal `act()` equivalent for early translated tests.

    As the scheduler/reconciler grows, this becomes the single chokepoint
    for flushing pending work in a deterministic way.
    """
    if not is_act_environment_enabled():
        emit_warning(
            "The current testing environment is not configured to support act(...).",
            category=RuntimeWarning,
            stacklevel=2,
        )
    with act_scope():
        try:
            yield
        finally:
            if flush is not None:
                flush()


def act_call(callback: Callable[[], Any], *, flush: Callable[[], None] | None = None) -> Any:
    """
    Run a callback inside a sync act scope and return its value.

    Minimal helper to match upstream `act(() => value)` return-value behavior.
    """
    if not is_act_environment_enabled():
        emit_warning(
            "The current testing environment is not configured to support act(...).",
            category=RuntimeWarning,
            stacklevel=2,
        )
    with act_scope():
        try:
            return callback()
        finally:
            if flush is not None:
                flush()


def act_async(
    callback: Callable[[], Any] | Callable[[], Awaitable[Any]],
    *,
    flush: Callable[[], None] | None = None,
    max_microtasks: int = 50,
) -> Any:
    """
    Minimal async `act()` equivalent (Phase 12).

    Runs an async callback (if provided) to completion, then yields to the event loop
    (microtask-ish) while flushing scheduled work until settled.
    """
    if max_microtasks < 0:
        raise ValueError("max_microtasks must be non-negative")
    if not is_act_environment_enabled():
        emit_warning(
            "The current testing environment is not configured to support act(...).",
            category=RuntimeWarning,
            stacklevel=2,
        )

    async def _run() -> Any:
        with act_scope():
            result = callback()
            if inspect.isawaitable(result):
                result = await result
            if flush is not None:
                flush()
            for _ in range(max_microtasks):
                await asyncio.sleep(0)
                if flush is not None:
                    flush()
            return result

    return asyncio.run(_run())
