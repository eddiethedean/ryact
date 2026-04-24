"""Shared timer/task heap work loop for MessageChannel / setImmediate / setTimeout harnesses."""

from __future__ import annotations

import heapq
from typing import Any, Optional, Protocol

from .scheduler_browser_flags import SchedulerBrowserFlags


class _BrowserStyleHeapDriver(Protocol):
    _flags: SchedulerBrowserFlags
    _task_heap: list[tuple[float, int, Any]]
    _timer_heap: list[tuple[float, int, Any]]
    _current_task: Any

    def _now(self) -> float: ...

    def unstable_should_yield(self) -> bool: ...


def advance_timers(
    timer_heap: list[tuple[float, int, Any]],
    task_heap: list[tuple[float, int, Any]],
    current_time: float,
) -> None:
    while timer_heap and timer_heap[0][0] <= current_time:
        _, _, timer = heapq.heappop(timer_heap)
        if timer.callback is None:
            continue
        heapq.heappush(task_heap, (timer.expiration_time, timer.id, timer))


def peek_task(task_heap: list[tuple[float, int, Any]]) -> Optional[Any]:
    while task_heap:
        _, _, t = task_heap[0]
        if t.callback is not None:
            return t
        heapq.heappop(task_heap)
    return None


def browser_style_work_loop(driver: _BrowserStyleHeapDriver, initial_time: float) -> bool:
    current_time = initial_time
    advance_timers(driver._timer_heap, driver._task_heap, current_time)
    driver._current_task = peek_task(driver._task_heap)
    while driver._current_task is not None:
        if not driver._flags.enable_always_yield_scheduler and (
            driver._current_task.expiration_time > current_time and driver.unstable_should_yield()
        ):
            break
        cb = driver._current_task.callback
        if callable(cb):
            driver._current_task.callback = None
            did_timeout = driver._current_task.expiration_time <= current_time
            cont = cb(did_timeout)
            current_time = driver._now()
            if callable(cont):
                driver._current_task.callback = cont
                advance_timers(driver._timer_heap, driver._task_heap, current_time)
                return True
            if driver._task_heap and driver._task_heap[0][2] is driver._current_task:
                heapq.heappop(driver._task_heap)
            advance_timers(driver._timer_heap, driver._task_heap, current_time)
        else:
            if driver._task_heap and driver._task_heap[0][2] is driver._current_task:
                heapq.heappop(driver._task_heap)
            advance_timers(driver._timer_heap, driver._task_heap, current_time)
        driver._current_task = peek_task(driver._task_heap)
        if driver._flags.enable_always_yield_scheduler:
            nxt = peek_task(driver._task_heap)
            if nxt is None or nxt.expiration_time > current_time:
                break
    return peek_task(driver._task_heap) is not None
