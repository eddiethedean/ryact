"""
Mock host for ``SchedulerSetImmediate-test.js`` parity (``setImmediate`` macrotask path).

Mirrors ``installMockBrowserRuntime`` in upstream
``packages/scheduler/src/__tests__/SchedulerSetImmediate-test.js``.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any, Optional


@dataclass
class SetImmediateMockRuntime:
    """Event log, virtual time, single pending ``setImmediate``, and ``setTimeout`` stubs."""

    _event_log: list[str] = field(default_factory=list)
    _current_time: float = 0.0
    _timer_id: int = field(default=0, init=False)
    _pending_immediate: Optional[Callable[[], None]] = field(default=None, init=False)
    _work_fn: Optional[Callable[[], None]] = field(default=None, init=False)

    def __post_init__(self) -> None:
        self.performance = SimpleNamespace(now=self._performance_now)

    def _performance_now(self) -> float:
        return self._current_time

    def advance_time(self, ms: float) -> None:
        self._current_time += ms

    def reset_time(self) -> None:
        self._current_time = 0.0

    def log(self, val: str) -> None:
        self._event_log.append(val)

    def is_log_empty(self) -> bool:
        return len(self._event_log) == 0

    def assert_log(self, expected: list[str]) -> None:
        actual = self._event_log
        self._event_log = []
        assert actual == expected, f"expected {expected!r} got {actual!r}"

    def _ensure_log_empty(self) -> None:
        if self._event_log:
            raise RuntimeError("Log is not empty. Call assertLog before continuing.")

    def set_on_immediate(self, fn: Optional[Callable[[], None]]) -> None:
        self._work_fn = fn

    def schedule_immediate(self) -> None:
        if self._pending_immediate is not None:
            raise RuntimeError("Message event already scheduled")
        self.log("Set Immediate")
        assert self._work_fn is not None
        self._pending_immediate = self._work_fn

    def fire_immediate(self) -> None:
        self._ensure_log_empty()
        if self._pending_immediate is None:
            raise RuntimeError("No setImmediate was scheduled")
        cb = self._pending_immediate
        self._pending_immediate = None
        self.log("setImmediate Callback")
        cb()

    def set_timeout(self, _cb: Callable[[], None], _delay: Any = None) -> int:
        tid = self._timer_id
        self._timer_id += 1
        self.log("Set Timer")
        return tid

    def clear_timeout(self, _id: int) -> None:
        pass
