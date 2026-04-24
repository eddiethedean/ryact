from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional, TypeVar

from .scheduler import (
    IDLE_PRIORITY,
    IMMEDIATE_PRIORITY,
    LOW_PRIORITY,
    NORMAL_PRIORITY,
    USER_BLOCKING_PRIORITY,
    Scheduler,
)

T = TypeVar("T")

# Upstream defaults (SchedulerFeatureFlags.js)
_DEFAULT_FRAME_YIELD_MS = 5


@dataclass(frozen=True)
class Task:
    """Opaque handle returned by `unstable_schedule_callback`."""

    _id: int
    _priority: int
    _start_time_ms: float
    _expiration_time_ms: float


_scheduler = Scheduler()
_cancelled: set[int] = set()

_current_priority_level: int = NORMAL_PRIORITY

# M18: expose these APIs, but host-accurate yielding lands in M19.
_needs_paint: bool = False
_frame_interval_ms: int = _DEFAULT_FRAME_YIELD_MS


def _validate_priority(priority_level: int) -> int:
    if priority_level in (
        IMMEDIATE_PRIORITY,
        USER_BLOCKING_PRIORITY,
        NORMAL_PRIORITY,
        LOW_PRIORITY,
        IDLE_PRIORITY,
    ):
        return priority_level
    return NORMAL_PRIORITY


def _timeout_ms(priority_level: int) -> float:
    # Mirrors upstream timeout table (Scheduler.js / SchedulerFeatureFlags.js)
    if priority_level == IMMEDIATE_PRIORITY:
        return -1.0
    if priority_level == USER_BLOCKING_PRIORITY:
        return 250.0
    if priority_level == NORMAL_PRIORITY:
        return 5000.0
    if priority_level == LOW_PRIORITY:
        return 10000.0
    if priority_level == IDLE_PRIORITY:
        return 1073741823.0
    return 5000.0


def unstable_now() -> float:
    """Return current time in milliseconds."""

    return _scheduler._now() * 1000.0  # type: ignore[attr-defined]


def unstable_get_current_priority_level() -> int:
    return _current_priority_level


def unstable_run_with_priority(priority_level: int, fn: Callable[[], T]) -> T:
    global _current_priority_level
    pl = _validate_priority(priority_level)
    prev = _current_priority_level
    _current_priority_level = pl
    try:
        return fn()
    finally:
        _current_priority_level = prev


def unstable_next(fn: Callable[[], T]) -> T:
    global _current_priority_level
    if _current_priority_level in (IMMEDIATE_PRIORITY, USER_BLOCKING_PRIORITY, NORMAL_PRIORITY):
        next_pl = NORMAL_PRIORITY
    else:
        next_pl = _current_priority_level
    prev = _current_priority_level
    _current_priority_level = next_pl
    try:
        return fn()
    finally:
        _current_priority_level = prev


def unstable_wrap_callback(callback: Callable[..., T]) -> Callable[..., T]:
    parent_priority = _current_priority_level

    def wrapped(*args: Any, **kwargs: Any) -> T:
        global _current_priority_level
        prev = _current_priority_level
        _current_priority_level = parent_priority
        try:
            return callback(*args, **kwargs)
        finally:
            _current_priority_level = prev

    return wrapped


def unstable_schedule_callback(
    priority_level: int,
    callback: Callable[[bool], Optional[Callable[[bool], Any]] | Any],
    options: Optional[dict[str, Any]] = None,
) -> Task:
    """
    Minimal port of upstream `unstable_scheduleCallback` (DOM fork).

    M18 intentionally does not implement the upstream host work loop; it uses the
    cooperative `schedulyr.Scheduler` drain API for execution.
    """

    pl = _validate_priority(priority_level)
    current_time_ms = unstable_now()

    delay_ms = 0.0
    if isinstance(options, dict):
        d = options.get("delay")
        if isinstance(d, (int, float)) and d > 0:
            delay_ms = float(d)

    start_time_ms = current_time_ms + delay_ms
    expiration_time_ms = start_time_ms + _timeout_ms(pl)

    tid: int = -1

    def run() -> None:
        nonlocal tid
        if tid in _cancelled:
            _cancelled.discard(tid)
            return
        did_timeout = expiration_time_ms <= unstable_now()
        result = callback(did_timeout)
        if callable(result):
            # Upstream yields to host immediately for continuations. In M18, we
            # reschedule immediately (host semantics are M19).
            unstable_schedule_callback(pl, result, options=None)

    tid = _scheduler.schedule_callback(pl, run, delay_ms=int(delay_ms))
    return Task(
        _id=tid,
        _priority=pl,
        _start_time_ms=start_time_ms,
        _expiration_time_ms=expiration_time_ms,
    )


def unstable_cancel_callback(task: Task) -> None:
    _cancelled.add(task._id)
    _scheduler.cancel_callback(task._id)


def unstable_should_yield() -> bool:
    # M18 conservative behavior: only yield if requestPaint was called. Time-slice
    # parity with upstream is implemented in M19.
    return _needs_paint


def unstable_request_paint() -> None:
    global _needs_paint
    _needs_paint = True


def unstable_force_frame_rate(fps: int) -> None:
    global _frame_interval_ms
    if fps < 0 or fps > 125:
        # Mirror upstream shape (logs error) but avoid printing in library code.
        return
    _frame_interval_ms = int(1000 / fps) if fps > 0 else _DEFAULT_FRAME_YIELD_MS

