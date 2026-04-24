from __future__ import annotations

import heapq
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Optional

IMMEDIATE_PRIORITY = 1
USER_BLOCKING_PRIORITY = 2
NORMAL_PRIORITY = 3
LOW_PRIORITY = 4
IDLE_PRIORITY = 5

# Priority timeouts match React ``Scheduler.js`` / ``UnstableMockScheduler`` (milliseconds
# in upstream; here converted to seconds because ``now()`` is wall seconds).
_MS = 1.0 / 1000.0
_MAX_SIGNED_31_MS = 1073741823.0


def _expiration_offset_seconds(priority: int) -> float:
    """``expiration_time = start_time + offset`` (same numeric policy as mock fork)."""
    if priority == IMMEDIATE_PRIORITY:
        return -1.0 * _MS
    if priority == USER_BLOCKING_PRIORITY:
        return 250.0 * _MS
    if priority == NORMAL_PRIORITY:
        return 5000.0 * _MS
    if priority == LOW_PRIORITY:
        return 10000.0 * _MS
    if priority == IDLE_PRIORITY:
        return _MAX_SIGNED_31_MS * _MS
    return 5000.0 * _MS


@dataclass
class _Task:
    """Internal node: timer heap sorts by ``start_time``; task heap by ``expiration_time``."""

    id: int
    priority: int
    callback: Optional[Callable[[], Any]]
    start_time: float
    expiration_time: float


def _advance_timers(
    timer_heap: list[tuple[float, int, _Task]],
    task_heap: list[tuple[float, int, _Task]],
    current_time: float,
    cancelled: set[int],
) -> None:
    """Promote due timers into the task heap (React ``advanceTimers``)."""
    while timer_heap:
        _, tid, task = timer_heap[0]
        if tid in cancelled or task.callback is None:
            heapq.heappop(timer_heap)
            continue
        if task.start_time > current_time:
            break
        heapq.heappop(timer_heap)
        heapq.heappush(task_heap, (task.expiration_time, tid, task))


def _pop_dead_task_head(
    task_heap: list[tuple[float, int, _Task]], cancelled: set[int]
) -> None:
    while task_heap:
        _, tid, task = task_heap[0]
        if tid not in cancelled and task.callback is not None:
            return
        heapq.heappop(task_heap)
        if tid in cancelled:
            cancelled.discard(tid)


def _pop_dead_timer_head(
    timer_heap: list[tuple[float, int, _Task]], cancelled: set[int]
) -> None:
    while timer_heap:
        _, tid, task = timer_heap[0]
        if tid not in cancelled and task.callback is not None:
            return
        heapq.heappop(timer_heap)
        if tid in cancelled:
            cancelled.discard(tid)


class Scheduler:
    """
    Cooperative scheduler with injectable ``now``.

    Uses a **timer queue** and **task queue** (min-heaps) matching React production
    ``Scheduler.js``: delayed work sits in the timer heap until ``start_time``; then
    it is promoted to the task heap ordered by ``expiration_time`` (``start_time`` +
    priority timeout), then ``id`` — equivalent to the historical single-heap
    ``(due, priority, task_id, callback)`` ordering for this package's public API.

    ``delay_ms`` is clamped to ``>= 0``. ``cancel_callback`` lazily skips tasks.
    If a scheduled callback returns another callable, it is queued as new work
    (same priority, ``start_time`` / ``expiration`` from ``now()`` after the callback),
    modeling a minimal continuation.

    ``time_slice_ms`` caps wall time checked before each task and after each callback.
    ``time_slice_ms=0`` means the deadline equals ``now()`` at entry, so no callbacks
    run unless ``now`` changes before the first check.
    """

    def __init__(self, now: Optional[Callable[[], float]] = None) -> None:
        self._now = time.monotonic if now is None else now
        self._next_id = 1
        self._timer_heap: list[tuple[float, int, _Task]] = []
        self._task_heap: list[tuple[float, int, _Task]] = []
        self._cancelled: set[int] = set()

    def schedule_callback(
        self, priority: int, callback: Callable[[], Any], delay_ms: int = 0
    ) -> int:
        if delay_ms < 0:
            delay_ms = 0
        current_time = self._now()
        start_time = current_time + (delay_ms / 1000.0)
        expiration_time = start_time + _expiration_offset_seconds(priority)
        tid = self._next_id
        self._next_id += 1
        task = _Task(
            id=tid,
            priority=priority,
            callback=callback,
            start_time=start_time,
            expiration_time=expiration_time,
        )
        if start_time > current_time:
            heapq.heappush(self._timer_heap, (start_time, tid, task))
        else:
            heapq.heappush(self._task_heap, (expiration_time, tid, task))
        return tid

    def cancel_callback(self, task_id: int) -> None:
        """Mark a task as cancelled; it is skipped when popped (lazy deletion)."""
        self._cancelled.add(task_id)

    def run_until_idle(self, time_slice_ms: Optional[int] = None) -> None:
        deadline = None
        if time_slice_ms is not None:
            deadline = self._now() + (time_slice_ms / 1000.0)
        while True:
            if deadline is not None and self._now() >= deadline:
                return
            _advance_timers(self._timer_heap, self._task_heap, self._now(), self._cancelled)
            _pop_dead_task_head(self._task_heap, self._cancelled)
            _pop_dead_timer_head(self._timer_heap, self._cancelled)

            if not self._task_heap:
                if not self._timer_heap:
                    return
                _, _, t0 = self._timer_heap[0]
                if t0.start_time > self._now():
                    return
                continue

            if deadline is not None and self._now() >= deadline:
                return

            _, tid, task = heapq.heappop(self._task_heap)
            if tid in self._cancelled:
                self._cancelled.discard(tid)
                continue
            cb = task.callback
            if cb is None:
                continue

            result = cb()
            if result is not None and callable(result):
                nid = self._next_id
                self._next_id += 1
                nt = self._now()
                exp = nt + _expiration_offset_seconds(task.priority)
                cont_task = _Task(
                    id=nid,
                    priority=task.priority,
                    callback=result,
                    start_time=nt,
                    expiration_time=exp,
                )
                heapq.heappush(self._task_heap, (exp, nid, cont_task))
            if deadline is not None and self._now() >= deadline:
                return


default_scheduler = Scheduler()
