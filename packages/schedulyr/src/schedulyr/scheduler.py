from __future__ import annotations

import heapq
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Optional

IMMEDIATE_PRIORITY = 1
USER_BLOCKING_PRIORITY = 2
NORMAL_PRIORITY = 3
LOW_PRIORITY = 4
IDLE_PRIORITY = 5


@dataclass
class _Task:
    due: float
    priority: int
    id: int
    callback: Callable[[], None]


class Scheduler:
    """
    Minimal cooperative scheduler.

    This is intentionally tiny; translated tests will force the detailed semantics.
    """

    def __init__(self, now: Optional[Callable[[], float]] = None) -> None:
        self._now = time.monotonic if now is None else now
        self._next_id = 1
        self._heap = []  # type: list[tuple[float, int, int, Callable[[], None]]]

    def schedule_callback(
        self, priority: int, callback: Callable[[], None], delay_ms: int = 0
    ) -> int:
        tid = self._next_id
        self._next_id += 1
        due = self._now() + (delay_ms / 1000.0)
        heapq.heappush(self._heap, (due, priority, tid, callback))
        return tid

    def run_until_idle(self, time_slice_ms: Optional[int] = None) -> None:
        deadline = None
        if time_slice_ms is not None:
            deadline = self._now() + (time_slice_ms / 1000.0)
        while self._heap:
            if deadline is not None and self._now() >= deadline:
                return
            due, priority, tid, cb = heapq.heappop(self._heap)
            if due > self._now():
                heapq.heappush(self._heap, (due, priority, tid, cb))
                return
            cb()


default_scheduler = Scheduler()
