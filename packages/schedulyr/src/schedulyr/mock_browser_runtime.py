"""
Deterministic mock of browser globals used by React ``SchedulerBrowser`` tests.

Mirrors ``installMockBrowserRuntime`` in ``packages/scheduler/src/__tests__/Scheduler-test.js``.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any, Optional


@dataclass
class MockBrowserRuntime:
    """Event log + virtual time + MessageChannel-style ``postMessage`` scheduling."""

    _has_pending_message: bool = field(default=False, init=False)
    _is_firing_message: bool = field(default=False, init=False)
    _has_pending_discrete: bool = field(default=False, init=False)
    _has_pending_continuous: bool = field(default=False, init=False)
    _timer_id: int = field(default=0, init=False)
    _event_log: list[str] = field(default_factory=list, init=False)
    _current_time: float = field(default=0.0, init=False)
    _port1_onmessage: Optional[Callable[[], None]] = field(default=None, init=False)

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

    def set_on_message(self, fn: Optional[Callable[[], None]]) -> None:
        self._port1_onmessage = fn

    def port2_post_message(self, _payload: Any = None) -> None:
        if self._has_pending_message:
            raise RuntimeError("Message event already scheduled")
        self.log("Post Message")
        self._has_pending_message = True

    def _ensure_log_empty(self) -> None:
        if self._event_log:
            raise RuntimeError("Log is not empty. Call assertLog before continuing.")

    def fire_message_event(self) -> None:
        self._ensure_log_empty()
        if not self._has_pending_message:
            raise RuntimeError("No message event was scheduled")
        self._has_pending_message = False
        on_message = self._port1_onmessage
        self.log("Message Event")
        self._is_firing_message = True
        try:
            if on_message is not None:
                on_message()
        finally:
            self._is_firing_message = False
            if self._has_pending_discrete:
                self.log("Discrete Event")
                self._has_pending_discrete = False
            if self._has_pending_continuous:
                self.log("Continuous Event")
                self._has_pending_continuous = False

    def schedule_discrete_event(self) -> None:
        if self._is_firing_message:
            self._has_pending_discrete = True
        else:
            self.log("Discrete Event")

    def schedule_continuous_event(self) -> None:
        if self._is_firing_message:
            self._has_pending_continuous = True
        else:
            self.log("Continuous Event")

    def set_timeout(self, _cb: Callable[[], None], _delay: Any = None) -> int:
        tid = self._timer_id
        self._timer_id += 1
        self.log("Set Timer")
        return tid

    def clear_timeout(self, _id: int) -> None:
        pass
