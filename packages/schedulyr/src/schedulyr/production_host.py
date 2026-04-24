from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any, Protocol


class HostAPI(Protocol):
    """Minimal host primitives needed by the production DOM scheduler path."""

    performance: Any

    def set_timeout(self, cb: Callable[[], None], delay: Any = None) -> int: ...

    def clear_timeout(self, id_: int) -> None: ...


@dataclass
class SetTimeoutMockRuntime:
    """
    Deterministic `setTimeout(0)` host used by production host-loop tests.

    Mirrors the log strings asserted by upstream scheduler host tests:
    - `Set Timer`
    - `SetTimeout Callback`
    """

    _event_log: list[str] = field(default_factory=list)
    _current_time: float = 0.0
    _timer_id: int = field(default=0, init=False)
    _pending: list[Callable[[], None]] = field(default_factory=list, init=False)

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

    def set_timeout(self, cb: Callable[[], None], _delay: Any = None) -> int:
        tid = self._timer_id
        self._timer_id += 1
        self.log("Set Timer")
        self._pending.append(cb)
        return tid

    def clear_timeout(self, _id: int) -> None:
        # We don't model cancellation for this minimal runtime.
        pass

    def run_all_pending(self) -> None:
        self._ensure_log_empty()
        while self._pending:
            cb = self._pending.pop(0)
            self.log("SetTimeout Callback")
            cb()

