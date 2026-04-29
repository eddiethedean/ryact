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
from ryact.dev import is_dev

from .warnings import emit_warning

_microtask_queue: list[Callable[[], None]] = []


def queue_microtask(fn: Callable[[], None]) -> None:
    """Deterministic microtask queue used by translated act() tests."""
    _microtask_queue.append(fn)


def _drain_microtasks(*, max_tasks: int = 1000) -> None:
    ran = 0
    while _microtask_queue and ran < max_tasks:
        fn = _microtask_queue.pop(0)
        fn()
        ran += 1


def set_act_environment_enabled(value: bool) -> None:
    _set_act_environment_enabled(value)


@contextmanager
def act(flush: Callable[[], None] | None = None) -> Generator[None, None, None]:
    """
    Minimal `act()` equivalent for early translated tests.

    As the scheduler/reconciler grows, this becomes the single chokepoint
    for flushing pending work in a deterministic way.
    """
    if is_dev() and not is_act_environment_enabled():
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


def act_call(
    callback: Callable[[], Any],
    *,
    flush: Callable[[], None] | None = None,
    drain_microtasks: int = 0,
) -> Any:
    """
    Run a callback inside a sync act scope and return its value.

    Minimal helper to match upstream `act(() => value)` return-value behavior.
    """
    if is_dev() and not is_act_environment_enabled():
        emit_warning(
            "The current testing environment is not configured to support act(...).",
            category=RuntimeWarning,
            stacklevel=2,
        )
    if drain_microtasks < 0:
        raise ValueError("drain_microtasks must be non-negative")
    with act_scope():
        try:
            result = callback()
            if inspect.isawaitable(result):
                emit_warning(
                    "A promise/awaitable was returned from a non-awaited act(...) scope. "
                    "Did you mean to await act_async(...) or await the returned awaitable?",
                    category=RuntimeWarning,
                    stacklevel=2,
                )
            return result
        finally:
            if flush is not None:
                flush()
            if drain_microtasks:
                for _ in range(drain_microtasks):
                    _drain_microtasks()
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
    if is_dev() and not is_act_environment_enabled():
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
                _drain_microtasks()
                if flush is not None:
                    flush()
            return result

    # Support nested usage: if we're already inside an event loop, return an awaitable
    # for the caller to await.
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(_run())
    else:
        return _run()
