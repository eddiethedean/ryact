"""
Event log for ``SchedulerProfiling.js`` parity (``Int32Array`` opcode stream).

Times are **microseconds** (``ms * 1000`` from mock ``currentTime`` in milliseconds).
"""

from __future__ import annotations

import struct
from collections.abc import Callable
from typing import Optional

# Match packages/scheduler/src/SchedulerProfiling.js
INITIAL_EVENT_LOG_SIZE = 131072
MAX_EVENT_LOG_SIZE = 524288

TASK_START_EVENT = 1
TASK_COMPLETE_EVENT = 2
TASK_ERROR_EVENT = 3
TASK_CANCEL_EVENT = 4
TASK_RUN_EVENT = 5
TASK_YIELD_EVENT = 6
SCHEDULER_SUSPEND_EVENT = 7
SCHEDULER_RESUME_EVENT = 8

PROFILING_OVERFLOW_MESSAGE = (
    "Scheduler Profiling: Event log exceeded maximum size. Don't forget "
    "to call `stopLoggingProfilingEvents()`."
)


class SchedulerProfilingBuffer:
    """Growable int32 event log; mirrors upstream ``logEvent`` / ``stopLoggingProfilingEvents``."""

    __slots__ = (
        "_buf",
        "_index",
        "_capacity",
        "_max_capacity",
        "_run_id_counter",
        "_main_thread_id_counter",
        "_on_overflow",
    )

    def __init__(self, *, max_capacity: int = MAX_EVENT_LOG_SIZE) -> None:
        self._buf: Optional[list[int]] = None
        self._index = 0
        self._capacity = 0
        self._max_capacity = max_capacity
        self._run_id_counter = 0
        self._main_thread_id_counter = 0
        self._on_overflow: Optional[Callable[[], None]] = None

    @property
    def active(self) -> bool:
        return self._buf is not None

    def set_overflow_handler(self, fn: Optional[Callable[[], None]]) -> None:
        self._on_overflow = fn

    def start(self) -> None:
        self._run_id_counter = 0
        self._main_thread_id_counter = 0
        self._capacity = min(INITIAL_EVENT_LOG_SIZE, self._max_capacity)
        self._buf = [0] * self._capacity
        self._index = 0

    def stop(self) -> Optional[bytes]:
        if self._buf is None:
            return None
        raw = self._buf[: self._index]
        self._buf = None
        self._capacity = 0
        self._index = 0
        return struct.pack(f"<{len(raw)}i", *raw) if raw else b""

    def _overflow_clear(self) -> None:
        if self._on_overflow is not None:
            self._on_overflow()
        self._buf = None
        self._capacity = 0
        self._index = 0

    def _ensure(self, need: int) -> bool:
        assert self._buf is not None
        if self._index + need <= self._capacity:
            return True
        new_cap = self._capacity
        while self._index + need > new_cap:
            new_cap *= 2
            if new_cap > self._max_capacity:
                self._overflow_clear()
                return False
        self._buf.extend([0] * (new_cap - self._capacity))
        self._capacity = new_cap
        return True

    def _append(self, entries: list[int]) -> None:
        if self._buf is None:
            return
        if not self._ensure(len(entries)):
            return
        n = len(entries)
        self._buf[self._index : self._index + n] = entries
        self._index += n

    def _time_us(self, ms: float) -> int:
        return int(ms * 1000)

    def mark_task_start(self, task_id: int, priority_level: int, ms: float) -> None:
        if self._buf is None:
            return
        self._append([TASK_START_EVENT, self._time_us(ms), task_id, int(priority_level)])

    def mark_task_completed(self, task_id: int, ms: float) -> None:
        if self._buf is None:
            return
        self._append([TASK_COMPLETE_EVENT, self._time_us(ms), task_id])

    def mark_task_canceled(self, task_id: int, ms: float) -> None:
        if self._buf is None:
            return
        self._append([TASK_CANCEL_EVENT, self._time_us(ms), task_id])

    def mark_task_errored(self, task_id: int, ms: float) -> None:
        if self._buf is None:
            return
        self._append([TASK_ERROR_EVENT, self._time_us(ms), task_id])

    def mark_task_run(self, task_id: int, ms: float) -> None:
        self._run_id_counter += 1
        if self._buf is None:
            return
        rid = self._run_id_counter
        self._append([TASK_RUN_EVENT, self._time_us(ms), task_id, rid])

    def mark_task_yield(self, task_id: int, ms: float) -> None:
        if self._buf is None:
            return
        rid = self._run_id_counter
        self._append([TASK_YIELD_EVENT, self._time_us(ms), task_id, rid])

    def mark_scheduler_suspended(self, ms: float) -> None:
        self._main_thread_id_counter += 1
        if self._buf is None:
            return
        mid = self._main_thread_id_counter
        self._append([SCHEDULER_SUSPEND_EVENT, self._time_us(ms), mid])

    def mark_scheduler_unsuspended(self, ms: float) -> None:
        if self._buf is None:
            return
        mid = self._main_thread_id_counter
        self._append([SCHEDULER_RESUME_EVENT, self._time_us(ms), mid])


class ProfilingEventLogger:
    """``unstable_Profiling``-shaped API bound to a :class:`SchedulerProfilingBuffer`."""

    __slots__ = ("_buffer", "_emit_overflow_warning")

    def __init__(
        self,
        buffer: SchedulerProfilingBuffer,
        *,
        emit_overflow_warning: Callable[[], None],
    ) -> None:
        self._buffer = buffer
        self._emit_overflow_warning = emit_overflow_warning

    def start_logging_profiling_events(self) -> None:
        self._buffer.set_overflow_handler(self._emit_overflow_warning)
        self._buffer.start()

    def stop_logging_profiling_events(self) -> Optional[bytes]:
        return self._buffer.stop()
