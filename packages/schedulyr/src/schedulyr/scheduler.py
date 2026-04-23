from __future__ import annotations

import heapq
import time
from collections.abc import Callable
from typing import Any, Optional

IMMEDIATE_PRIORITY = 1
USER_BLOCKING_PRIORITY = 2
NORMAL_PRIORITY = 3
LOW_PRIORITY = 4
IDLE_PRIORITY = 5

# Min-heap tuple order: (due, priority, task_id, callback).
# Earlier due runs first; ties break by lower numeric priority (more urgent);
# then by monotonic task_id for FIFO among identical (due, priority).


class Scheduler:
    """
    Cooperative scheduler with injectable ``now``.

    Heap ordering is ``(due, priority, task_id, callback)`` — see module comment.

    ``delay_ms`` is clamped to ``>= 0``. ``cancel_callback`` lazily skips tasks.
    If a scheduled callback returns another callable, it is queued as new work
    (same priority, due immediately after ``now()``), modeling a minimal continuation.
    """

    def __init__(self, now: Optional[Callable[[], float]] = None) -> None:
        self._now = time.monotonic if now is None else now
        self._next_id = 1
        self._heap: list[tuple[float, int, int, Callable[[], Any]]] = []
        self._cancelled: set[int] = set()

    def schedule_callback(
        self, priority: int, callback: Callable[[], Any], delay_ms: int = 0
    ) -> int:
        if delay_ms < 0:
            delay_ms = 0
        tid = self._next_id
        self._next_id += 1
        due = self._now() + (delay_ms / 1000.0)
        heapq.heappush(self._heap, (due, priority, tid, callback))
        return tid

    def cancel_callback(self, task_id: int) -> None:
        """Mark a task as cancelled; it is skipped when popped (lazy deletion)."""
        self._cancelled.add(task_id)

    def run_until_idle(self, time_slice_ms: Optional[int] = None) -> None:
        """
        Drain due work until the heap is empty, the next task is not yet due,
        or a ``time_slice_ms`` deadline is reached.

        The deadline is checked before each task and after each callback runs
        (so work inside a callback that advances ``now`` can trigger a yield).
        ``time_slice_ms=0`` means the deadline equals ``now()`` at entry, so no
        callbacks run unless ``now`` changes before the first check (use a
        non-zero slice to run work).
        """
        deadline = None
        if time_slice_ms is not None:
            deadline = self._now() + (time_slice_ms / 1000.0)
        while self._heap:
            if deadline is not None and self._now() >= deadline:
                return
            due, priority, tid, cb = heapq.heappop(self._heap)
            if tid in self._cancelled:
                self._cancelled.discard(tid)
                continue
            if due > self._now():
                heapq.heappush(self._heap, (due, priority, tid, cb))
                return
            result = cb()
            if result is not None and callable(result):
                nid = self._next_id
                self._next_id += 1
                heapq.heappush(
                    self._heap,
                    (self._now(), priority, nid, result),
                )
            if deadline is not None and self._now() >= deadline:
                return


default_scheduler = Scheduler()
