from __future__ import annotations

import heapq
from dataclasses import dataclass, field
from typing import Callable, List, Tuple


@dataclass
class _Timer:
    due_ms: int
    id: int
    callback: Callable[[], None] = field(compare=False)


class FakeTimers:
    def __init__(self) -> None:
        self._now_ms = 0
        self._next_id = 1
        self._heap = []  # type: List[Tuple[int, int, Callable[[], None]]]

    @property
    def now_ms(self) -> int:
        return self._now_ms

    def set_timeout(self, callback: Callable[[], None], delay_ms: int) -> int:
        tid = self._next_id
        self._next_id += 1
        heapq.heappush(self._heap, (self._now_ms + delay_ms, tid, callback))
        return tid

    def now_seconds(self) -> float:
        return self._now_ms / 1000.0

    def advance(self, ms: int) -> None:
        target = self._now_ms + ms
        while self._heap and self._heap[0][0] <= target:
            due, _, cb = heapq.heappop(self._heap)
            self._now_ms = due
            cb()
        self._now_ms = target

