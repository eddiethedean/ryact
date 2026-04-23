"""
Port of React ``SchedulerMock.js`` (``scheduler/unstable_mock``).

Virtual-time cooperative scheduler with ``taskQueue`` / ``timerQueue`` min-heaps,
``unstable_flushExpired`` / ``unstable_flushAll`` / ``unstable_flushNumberOfYields`` /
``unstable_flushUntilNextPaint``, and a ``log`` sink used by translated
``SchedulerMock-test.js`` parity tests. Profiling hooks are omitted (``enableProfiling``
false in upstream test bundle).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional

from .scheduler import (
    IDLE_PRIORITY,
    IMMEDIATE_PRIORITY,
    LOW_PRIORITY,
    NORMAL_PRIORITY,
    USER_BLOCKING_PRIORITY,
)

_MAX_SIGNED_31 = 1073741823
_IMMEDIATE_PRIORITY_TIMEOUT = -1
_USER_BLOCKING_PRIORITY_TIMEOUT = 250.0
_NORMAL_PRIORITY_TIMEOUT = 5000.0
_LOW_PRIORITY_TIMEOUT = 10000.0
_IDLE_PRIORITY_TIMEOUT = float(_MAX_SIGNED_31)


def _compare_tasks(a: _MockTask, b: _MockTask) -> int:
    d = a.sort_index - b.sort_index
    return d if d != 0 else a.id - b.id


def _heap_push(heap: list[_MockTask], node: _MockTask) -> None:
    heap.append(node)
    index = len(heap) - 1
    while index > 0:
        parent_index = (index - 1) // 2
        parent = heap[parent_index]
        if _compare_tasks(parent, node) > 0:
            heap[parent_index] = node
            heap[index] = parent
            index = parent_index
        else:
            return


def _heap_pop(heap: list[_MockTask]) -> Optional[_MockTask]:
    if not heap:
        return None
    first = heap[0]
    last = heap.pop()
    if last is not first:
        heap[0] = last
        _sift_down(heap, last, 0)
    return first


def _heap_peek(heap: list[_MockTask]) -> Optional[_MockTask]:
    return heap[0] if heap else None


def _sift_down(heap: list[_MockTask], node: _MockTask, i: int) -> None:
    index = i
    length = len(heap)
    half = length // 2
    while index < half:
        left_index = (index + 1) * 2 - 1
        left = heap[left_index]
        right_index = left_index + 1
        right = heap[right_index] if right_index < length else None

        if _compare_tasks(left, node) < 0:
            if right is not None and _compare_tasks(right, left) < 0:
                heap[index] = right
                heap[right_index] = node
                index = right_index
            else:
                heap[index] = left
                heap[left_index] = node
                index = left_index
        elif right is not None and _compare_tasks(right, node) < 0:
            heap[index] = right
            heap[right_index] = node
            index = right_index
        else:
            return


@dataclass
class _MockTask:
    id: int
    callback: Optional[Any]
    priority_level: int
    start_time: float
    expiration_time: float
    sort_index: float


@dataclass
class MockScheduledTask:
    """Opaque handle for ``unstable_cancel_callback`` (wraps internal task)."""

    _task: _MockTask


class UnstableMockScheduler:
    """
    Mutable bundle mirroring React's mock scheduler module state.

    Use one instance per test; call ``reset()`` if reusing (not typical in pytest).
    """

    __slots__ = (
        "_task_queue",
        "_timer_queue",
        "_task_id_counter",
        "_current_task",
        "_current_priority_level",
        "_is_performing_work",
        "_is_host_callback_scheduled",
        "_is_host_timeout_scheduled",
        "_current_mock_time",
        "_scheduled_callback",
        "_scheduled_timeout",
        "_timeout_time",
        "_yielded_values",
        "_expected_number_of_yields",
        "_did_stop",
        "_is_flushing",
        "_needs_paint",
        "_should_yield_for_paint",
        "_disable_yield_value",
    )

    def __init__(self) -> None:
        self._task_queue: list[_MockTask] = []
        self._timer_queue: list[_MockTask] = []
        self._task_id_counter = 1
        self._current_task: Optional[_MockTask] = None
        self._current_priority_level = NORMAL_PRIORITY
        self._is_performing_work = False
        self._is_host_callback_scheduled = False
        self._is_host_timeout_scheduled = False
        self._current_mock_time = 0.0
        self._scheduled_callback: Optional[Callable[[bool, float], bool]] = None
        self._scheduled_timeout: Optional[Callable[[float], None]] = None
        self._timeout_time = -1.0
        self._yielded_values: Optional[list[Any]] = None
        self._expected_number_of_yields = -1
        self._did_stop = False
        self._is_flushing = False
        self._needs_paint = False
        self._should_yield_for_paint = False
        self._disable_yield_value = False

    # --- public unstable API (snake_case Python style) ---

    def unstable_run_with_priority(self, priority_level: int, fn: Callable[[], Any]) -> Any:
        pl = self._normalize_priority(priority_level)
        prev = self._current_priority_level
        self._current_priority_level = pl
        try:
            return fn()
        finally:
            self._current_priority_level = prev

    def unstable_wrap_callback(self, callback: Callable[..., Any]) -> Callable[..., Any]:
        parent_priority = self._current_priority_level

        def wrapped(*args: Any, **kwargs: Any) -> Any:
            prev = self._current_priority_level
            self._current_priority_level = parent_priority
            try:
                return callback(*args, **kwargs)
            finally:
                self._current_priority_level = prev

        return wrapped

    def unstable_schedule_callback(
        self,
        priority_level: int,
        callback: Any,
        options: Optional[dict[str, Any]] = None,
    ) -> MockScheduledTask:
        pl = self._normalize_priority(priority_level)
        current_time = self._get_current_time()
        start_time = current_time
        if isinstance(options, dict) and options is not None:
            delay = options.get("delay")
            if isinstance(delay, (int, float)) and delay > 0:
                start_time = current_time + float(delay)

        timeout = self._timeout_for_priority(pl)
        expiration_time = start_time + timeout

        new_task = _MockTask(
            id=self._task_id_counter,
            callback=callback,
            priority_level=pl,
            start_time=start_time,
            expiration_time=expiration_time,
            sort_index=-1.0,
        )
        self._task_id_counter += 1

        if start_time > current_time:
            new_task.sort_index = start_time
            _heap_push(self._timer_queue, new_task)
            if _heap_peek(self._task_queue) is None and new_task is _heap_peek(self._timer_queue):
                if self._is_host_timeout_scheduled:
                    self._cancel_host_timeout()
                else:
                    self._is_host_timeout_scheduled = True
                self._request_host_timeout(self._handle_timeout, start_time - current_time)
        else:
            new_task.sort_index = expiration_time
            _heap_push(self._task_queue, new_task)
            if not self._is_host_callback_scheduled and not self._is_performing_work:
                self._is_host_callback_scheduled = True
                self._request_host_callback(self._flush_work)

        return MockScheduledTask(_task=new_task)

    def unstable_cancel_callback(self, task: MockScheduledTask) -> None:
        task._task.callback = None

    def unstable_get_current_priority_level(self) -> int:
        return self._current_priority_level

    def unstable_should_yield(self) -> bool:
        return self._should_yield_to_host()

    def unstable_request_paint(self) -> None:
        self._needs_paint = True

    def unstable_now(self) -> float:
        return self._get_current_time()

    def unstable_advance_time(self, ms: float) -> None:
        if self._disable_yield_value:
            return
        self._current_mock_time += ms
        if self._scheduled_timeout is not None and self._timeout_time <= self._current_mock_time:
            st = self._scheduled_timeout
            ct = self._current_mock_time
            self._timeout_time = -1.0
            self._scheduled_timeout = None
            st(ct)

    def unstable_flush_expired(self) -> None:
        if self._is_flushing:
            raise RuntimeError("Already flushing work.")
        if self._scheduled_callback is not None:
            self._is_flushing = True
            try:
                has_more = self._scheduled_callback(False, self._current_mock_time)
                if not has_more:
                    self._scheduled_callback = None
            finally:
                self._is_flushing = False

    def unstable_flush_all_without_asserting(self) -> bool:
        if self._is_flushing:
            raise RuntimeError("Already flushing work.")
        if self._scheduled_callback is not None:
            cb = self._scheduled_callback
            self._is_flushing = True
            try:
                has_more_work = True
                while has_more_work:
                    has_more_work = cb(True, self._current_mock_time)
                if not has_more_work:
                    self._scheduled_callback = None
                return True
            finally:
                self._is_flushing = False
        return False

    def unstable_flush_number_of_yields(self, count: int) -> None:
        if self._is_flushing:
            raise RuntimeError("Already flushing work.")
        if self._scheduled_callback is not None:
            cb = self._scheduled_callback
            self._expected_number_of_yields = count
            self._is_flushing = True
            try:
                has_more_work = True
                while has_more_work and not self._did_stop:
                    has_more_work = cb(True, self._current_mock_time)
                if not has_more_work:
                    self._scheduled_callback = None
            finally:
                self._expected_number_of_yields = -1
                self._did_stop = False
                self._is_flushing = False

    def unstable_flush_until_next_paint(self) -> bool:
        if self._is_flushing:
            raise RuntimeError("Already flushing work.")
        if self._scheduled_callback is not None:
            cb = self._scheduled_callback
            self._should_yield_for_paint = True
            self._needs_paint = False
            self._is_flushing = True
            try:
                has_more_work = True
                while has_more_work and not self._did_stop:
                    has_more_work = cb(True, self._current_mock_time)
                if not has_more_work:
                    self._scheduled_callback = None
            finally:
                self._should_yield_for_paint = False
                self._did_stop = False
                self._is_flushing = False
        return False

    def unstable_has_pending_work(self) -> bool:
        return self._scheduled_callback is not None

    def unstable_flush_all(self) -> None:
        if self._yielded_values is not None:
            raise RuntimeError(
                "Log is not empty. Assert on the log of yielded values before "
                "flushing additional work."
            )
        self.unstable_flush_all_without_asserting()
        if self._yielded_values is not None:
            raise RuntimeError(
                "While flushing work, something yielded a value. Use an "
                "assertion helper to assert on the log of yielded values."
            )

    def unstable_clear_log(self) -> list[Any]:
        if self._yielded_values is None:
            return []
        values = self._yielded_values
        self._yielded_values = None
        return values

    def log(self, value: Any) -> None:
        if self._disable_yield_value:
            return
        if self._yielded_values is None:
            self._yielded_values = [value]
        else:
            self._yielded_values.append(value)

    def reset(self) -> None:
        if self._is_flushing:
            raise RuntimeError("Cannot reset while already flushing work.")
        self._task_queue.clear()
        self._timer_queue.clear()
        self._task_id_counter = 1
        self._current_task = None
        self._current_priority_level = NORMAL_PRIORITY
        self._is_performing_work = False
        self._is_host_callback_scheduled = False
        self._is_host_timeout_scheduled = False
        self._current_mock_time = 0.0
        self._scheduled_callback = None
        self._scheduled_timeout = None
        self._timeout_time = -1.0
        self._yielded_values = None
        self._expected_number_of_yields = -1
        self._did_stop = False
        self._is_flushing = False
        self._needs_paint = False
        self._should_yield_for_paint = False

    # --- internal ---

    def _normalize_priority(self, priority_level: int) -> int:
        if priority_level not in (
            IMMEDIATE_PRIORITY,
            USER_BLOCKING_PRIORITY,
            NORMAL_PRIORITY,
            LOW_PRIORITY,
            IDLE_PRIORITY,
        ):
            return NORMAL_PRIORITY
        return priority_level

    def _timeout_for_priority(self, priority_level: int) -> float:
        if priority_level == IMMEDIATE_PRIORITY:
            return float(_IMMEDIATE_PRIORITY_TIMEOUT)
        if priority_level == USER_BLOCKING_PRIORITY:
            return _USER_BLOCKING_PRIORITY_TIMEOUT
        if priority_level == IDLE_PRIORITY:
            return _IDLE_PRIORITY_TIMEOUT
        if priority_level == LOW_PRIORITY:
            return _LOW_PRIORITY_TIMEOUT
        return _NORMAL_PRIORITY_TIMEOUT

    def _get_current_time(self) -> float:
        return self._current_mock_time

    def _request_host_callback(self, callback: Callable[[bool, float], bool]) -> None:
        self._scheduled_callback = callback

    def _request_host_timeout(self, callback: Callable[[float], None], ms: float) -> None:
        self._scheduled_timeout = callback
        self._timeout_time = self._current_mock_time + ms

    def _cancel_host_timeout(self) -> None:
        self._scheduled_timeout = None
        self._timeout_time = -1.0

    def _should_yield_to_host(self) -> bool:
        if (
            (self._expected_number_of_yields == 0 and self._yielded_values is None)
            or (
                self._expected_number_of_yields != -1
                and self._yielded_values is not None
                and len(self._yielded_values) >= self._expected_number_of_yields
            )
            or (self._should_yield_for_paint and self._needs_paint)
        ):
            self._did_stop = True
            return True
        return False

    def _advance_timers(self, current_time: float) -> None:
        timer = _heap_peek(self._timer_queue)
        while timer is not None:
            if timer.callback is None:
                _heap_pop(self._timer_queue)
            elif timer.start_time <= current_time:
                _heap_pop(self._timer_queue)
                timer.sort_index = timer.expiration_time
                _heap_push(self._task_queue, timer)
            else:
                return
            timer = _heap_peek(self._timer_queue)

    def _handle_timeout(self, current_time: float) -> None:
        self._is_host_timeout_scheduled = False
        self._advance_timers(current_time)

        if not self._is_host_callback_scheduled:
            if _heap_peek(self._task_queue) is not None:
                self._is_host_callback_scheduled = True
                self._request_host_callback(self._flush_work)
            else:
                first_timer = _heap_peek(self._timer_queue)
                if first_timer is not None:
                    self._request_host_timeout(
                        self._handle_timeout, first_timer.start_time - current_time
                    )

    def _flush_work(self, has_time_remaining: bool, initial_time: float) -> bool:
        self._is_host_callback_scheduled = False
        if self._is_host_timeout_scheduled:
            self._is_host_timeout_scheduled = False
            self._cancel_host_timeout()

        self._is_performing_work = True
        prev_priority = self._current_priority_level
        try:
            return self._work_loop(has_time_remaining, initial_time)
        finally:
            self._current_task = None
            self._current_priority_level = prev_priority
            self._is_performing_work = False

    def _work_loop(self, has_time_remaining: bool, initial_time: float) -> bool:
        current_time = initial_time
        self._advance_timers(current_time)
        self._current_task = _heap_peek(self._task_queue)
        while self._current_task is not None:
            ct = self._current_task
            if ct.expiration_time > current_time and (
                not has_time_remaining or self._should_yield_to_host()
            ):
                break
            callback = ct.callback
            if callable(callback):
                ct.callback = None
                self._current_priority_level = ct.priority_level
                did_user_callback_timeout = ct.expiration_time <= current_time
                continuation_callback = callback(did_user_callback_timeout)
                current_time = self._get_current_time()
                if callable(continuation_callback):
                    ct.callback = continuation_callback
                    self._advance_timers(current_time)
                    if self._should_yield_for_paint:
                        self._needs_paint = True
                        return True
                else:
                    if ct is _heap_peek(self._task_queue):
                        _heap_pop(self._task_queue)
                    self._advance_timers(current_time)
            else:
                _heap_pop(self._task_queue)
            self._current_task = _heap_peek(self._task_queue)

        if self._current_task is not None:
            return True
        first_timer = _heap_peek(self._timer_queue)
        if first_timer is not None:
            self._request_host_timeout(
                self._handle_timeout, first_timer.start_time - current_time
            )
        return False
