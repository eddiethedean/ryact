"""
``Scheduler.js`` harness for the ``setImmediate`` host path (``SchedulerSetImmediate-test.js``).

Work loop matches :class:`BrowserSchedulerHarness`; macrotask driver uses
:class:`SetImmediateMockRuntime` instead of ``MessageChannel``.
"""

from __future__ import annotations

import heapq
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Optional

from .browser_scheduler import ScheduledTaskHandle, SchedulerBrowserFlags
from .scheduler import (
    IDLE_PRIORITY,
    IMMEDIATE_PRIORITY,
    LOW_PRIORITY,
    NORMAL_PRIORITY,
    USER_BLOCKING_PRIORITY,
)
from .set_immediate_runtime import SetImmediateMockRuntime

_MAX_SIGNED_31 = 1073741823


@dataclass
class _Task:
    id: int
    callback: Optional[Callable[[bool], Any]]
    priority_level: int
    start_time: float
    expiration_time: float


class SetImmediateSchedulerHarness:
    """``unstable_*`` surface for ``setImmediate``-scheduled ``performWorkUntilDeadline``."""

    def __init__(
        self,
        host: SetImmediateMockRuntime,
        flags: Optional[SchedulerBrowserFlags] = None,
    ) -> None:
        self._host = host
        self._flags = flags or SchedulerBrowserFlags()
        self._task_heap: list[tuple[float, int, _Task]] = []
        self._timer_heap: list[tuple[float, int, _Task]] = []
        self._next_id = 1
        self._current_task: Optional[_Task] = None
        self._is_performing_work = False
        self._is_host_callback_scheduled = False
        self._is_message_loop_running = False
        self._needs_paint = False
        self._start_time = 0.0

        host.set_on_immediate(self.perform_work_until_deadline)

    def _now(self) -> float:
        return float(self._host.performance.now())

    def unstable_now(self) -> float:
        return self._now()

    def unstable_request_paint(self) -> None:
        if self._flags.enable_request_paint:
            self._needs_paint = True

    def unstable_should_yield(self) -> bool:
        if (
            not self._flags.enable_always_yield_scheduler
            and self._flags.enable_request_paint
            and self._needs_paint
        ):
            return True
        elapsed = self._now() - self._start_time
        return not elapsed < self._flags.frame_yield_ms

    def unstable_schedule_callback(
        self,
        priority_level: int,
        callback: Callable[[bool], Any],
        options: Any = None,
    ) -> ScheduledTaskHandle:
        current_time = self._now()
        start_time = current_time
        if isinstance(options, dict) and options.get("delay"):
            delay = float(options["delay"])
            if delay > 0:
                start_time = current_time + delay
        timeout = self._timeout_for_priority(priority_level)
        expiration_time = start_time + timeout
        tid = self._next_id
        self._next_id += 1
        task = _Task(
            id=tid,
            callback=callback,
            priority_level=priority_level,
            start_time=start_time,
            expiration_time=expiration_time,
        )
        if start_time > current_time:
            heapq.heappush(self._timer_heap, (start_time, tid, task))
        else:
            heapq.heappush(self._task_heap, (expiration_time, tid, task))
            if not self._is_host_callback_scheduled and not self._is_performing_work:
                self._is_host_callback_scheduled = True
                self._request_host_callback()
        return ScheduledTaskHandle(_task=task)

    def _timeout_for_priority(self, priority_level: int) -> float:
        if priority_level == IMMEDIATE_PRIORITY:
            return -1.0
        if priority_level == USER_BLOCKING_PRIORITY:
            return self._flags.user_blocking_priority_timeout
        if priority_level == IDLE_PRIORITY:
            return float(_MAX_SIGNED_31)
        if priority_level == LOW_PRIORITY:
            return self._flags.low_priority_timeout
        return self._flags.normal_priority_timeout

    def unstable_cancel_callback(self, handle: ScheduledTaskHandle) -> None:
        handle._task.callback = None

    def _request_host_callback(self) -> None:
        if not self._is_message_loop_running:
            self._is_message_loop_running = True
            self._host.schedule_immediate()

    def perform_work_until_deadline(self) -> None:
        if self._flags.enable_request_paint:
            self._needs_paint = False
        if not self._is_message_loop_running:
            return
        current_time = self._now()
        self._start_time = current_time
        exc: Optional[BaseException] = None
        has_more = True
        try:
            has_more = self._flush_work(current_time)
        except BaseException as e:
            exc = e
            has_more = True
        finally:
            if has_more:
                self._host.schedule_immediate()
            else:
                self._is_message_loop_running = False
        if exc is not None:
            raise exc

    def _flush_work(self, initial_time: float) -> bool:
        self._is_host_callback_scheduled = False
        self._is_performing_work = True
        try:
            return self._work_loop(initial_time)
        finally:
            self._current_task = None
            self._is_performing_work = False

    def _advance_timers(self, current_time: float) -> None:
        while self._timer_heap and self._timer_heap[0][0] <= current_time:
            _, _, timer = heapq.heappop(self._timer_heap)
            if timer.callback is None:
                continue
            heapq.heappush(self._task_heap, (timer.expiration_time, timer.id, timer))

    def _peek_task(self) -> Optional[_Task]:
        while self._task_heap:
            _, _, t = self._task_heap[0]
            if t.callback is not None:
                return t
            heapq.heappop(self._task_heap)
        return None

    def _work_loop(self, initial_time: float) -> bool:
        current_time = initial_time
        self._advance_timers(current_time)
        self._current_task = self._peek_task()
        while self._current_task is not None:
            if not self._flags.enable_always_yield_scheduler and (
                self._current_task.expiration_time > current_time and self.unstable_should_yield()
            ):
                break
            cb = self._current_task.callback
            if callable(cb):
                self._current_task.callback = None
                did_timeout = self._current_task.expiration_time <= current_time
                cont = cb(did_timeout)
                current_time = self._now()
                if callable(cont):
                    self._current_task.callback = cont
                    self._advance_timers(current_time)
                    return True
                if self._task_heap and self._task_heap[0][2] is self._current_task:
                    heapq.heappop(self._task_heap)
                self._advance_timers(current_time)
            else:
                if self._task_heap and self._task_heap[0][2] is self._current_task:
                    heapq.heappop(self._task_heap)
                self._advance_timers(current_time)
            self._current_task = self._peek_task()
            if self._flags.enable_always_yield_scheduler:
                nxt = self._peek_task()
                if nxt is None or nxt.expiration_time > current_time:
                    break
        return self._peek_task() is not None


unstable_NormalPriority = NORMAL_PRIORITY
unstable_UserBlockingPriority = USER_BLOCKING_PRIORITY
unstable_ImmediatePriority = IMMEDIATE_PRIORITY
unstable_LowPriority = LOW_PRIORITY
unstable_IdlePriority = IDLE_PRIORITY
