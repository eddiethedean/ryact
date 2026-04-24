"""
Parity with ``SchedulerPostTask`` in ``packages/scheduler/src/__tests__/SchedulerPostTask-test.js``.
"""

from __future__ import annotations

import pytest
from schedulyr.post_task_runtime import PostTaskMockRuntime
from schedulyr.post_task_scheduler import (
    PostTaskSchedulerHarness,
    unstable_IdlePriority,
    unstable_ImmediatePriority,
    unstable_LowPriority,
    unstable_NormalPriority,
    unstable_UserBlockingPriority,
)


def _js_bool(b: bool) -> str:
    return "true" if b else "false"


@pytest.fixture()
def rt() -> PostTaskMockRuntime:
    r = PostTaskMockRuntime()
    r.wire_default_yield()
    return r


@pytest.fixture()
def h(rt: PostTaskMockRuntime) -> PostTaskSchedulerHarness:
    return PostTaskSchedulerHarness(rt)


def test_task_that_finishes_before_deadline(
    h: PostTaskSchedulerHarness,
    rt: PostTaskMockRuntime,
) -> None:
    h.unstable_schedule_callback(unstable_NormalPriority, lambda _d: rt.log("A"))
    rt.assert_log(["Post Task 0 [user-visible]"])
    rt.flush_tasks()
    rt.assert_log(["Task 0 Fired", "A"])


def test_task_with_continuation(h: PostTaskSchedulerHarness, rt: PostTaskMockRuntime) -> None:
    shy = h.unstable_should_yield

    def task(_d: bool):
        rt.log("A")
        while not shy():
            rt.advance_time(1)
        rt.log(f"Yield at {int(h.unstable_now())}ms")
        return lambda _d2: rt.log("Continuation")

    h.unstable_schedule_callback(unstable_NormalPriority, task)
    rt.assert_log(["Post Task 0 [user-visible]"])
    rt.flush_tasks()
    rt.assert_log(
        [
            "Task 0 Fired",
            "A",
            "Yield at 5ms",
            "Yield 1 [user-visible]",
        ]
    )
    rt.flush_tasks()
    rt.assert_log(["Task 1 Fired", "Continuation"])


def test_multiple_tasks(h: PostTaskSchedulerHarness, rt: PostTaskMockRuntime) -> None:
    h.unstable_schedule_callback(unstable_NormalPriority, lambda _d: rt.log("A"))
    h.unstable_schedule_callback(unstable_NormalPriority, lambda _d: rt.log("B"))
    rt.assert_log(
        [
            "Post Task 0 [user-visible]",
            "Post Task 1 [user-visible]",
        ]
    )
    rt.flush_tasks()
    rt.assert_log(["Task 0 Fired", "A", "Task 1 Fired", "B"])


def test_cancels_tasks(h: PostTaskSchedulerHarness, rt: PostTaskMockRuntime) -> None:
    t = h.unstable_schedule_callback(unstable_NormalPriority, lambda _d: rt.log("A"))
    rt.assert_log(["Post Task 0 [user-visible]"])
    h.unstable_cancel_callback(t)
    rt.flush_tasks()
    rt.assert_log([])


def test_an_error_in_one_task_does_not_affect_execution_of_other_tasks(
    h: PostTaskSchedulerHarness,
    rt: PostTaskMockRuntime,
) -> None:
    def boom(_d: bool) -> None:
        raise RuntimeError("Oops!")

    h.unstable_schedule_callback(unstable_NormalPriority, boom)
    h.unstable_schedule_callback(unstable_NormalPriority, lambda _d: rt.log("Yay"))
    rt.assert_log(
        [
            "Post Task 0 [user-visible]",
            "Post Task 1 [user-visible]",
        ]
    )
    rt.flush_tasks()
    rt.assert_log(["Task 0 Fired", "Error: Oops!", "Task 1 Fired", "Yay"])


def test_schedule_new_task_after_queue_has_emptied(
    h: PostTaskSchedulerHarness,
    rt: PostTaskMockRuntime,
) -> None:
    h.unstable_schedule_callback(unstable_NormalPriority, lambda _d: rt.log("A"))
    rt.assert_log(["Post Task 0 [user-visible]"])
    rt.flush_tasks()
    rt.assert_log(["Task 0 Fired", "A"])
    h.unstable_schedule_callback(unstable_NormalPriority, lambda _d: rt.log("B"))
    rt.assert_log(["Post Task 1 [user-visible]"])
    rt.flush_tasks()
    rt.assert_log(["Task 1 Fired", "B"])


def test_schedule_new_task_after_a_cancellation(
    h: PostTaskSchedulerHarness,
    rt: PostTaskMockRuntime,
) -> None:
    handle = h.unstable_schedule_callback(unstable_NormalPriority, lambda _d: rt.log("A"))
    rt.assert_log(["Post Task 0 [user-visible]"])
    h.unstable_cancel_callback(handle)
    rt.flush_tasks()
    rt.assert_log([])
    h.unstable_schedule_callback(unstable_NormalPriority, lambda _d: rt.log("B"))
    rt.assert_log(["Post Task 1 [user-visible]"])
    rt.flush_tasks()
    rt.assert_log(["Task 1 Fired", "B"])


def test_schedules_tasks_at_different_priorities(
    h: PostTaskSchedulerHarness,
    rt: PostTaskMockRuntime,
) -> None:
    h.unstable_schedule_callback(unstable_ImmediatePriority, lambda _d: rt.log("A"))
    h.unstable_schedule_callback(unstable_UserBlockingPriority, lambda _d: rt.log("B"))
    h.unstable_schedule_callback(unstable_NormalPriority, lambda _d: rt.log("C"))
    h.unstable_schedule_callback(unstable_LowPriority, lambda _d: rt.log("D"))
    h.unstable_schedule_callback(unstable_IdlePriority, lambda _d: rt.log("E"))
    rt.assert_log(
        [
            "Post Task 0 [user-blocking]",
            "Post Task 1 [user-blocking]",
            "Post Task 2 [user-visible]",
            "Post Task 3 [user-visible]",
            "Post Task 4 [background]",
        ]
    )
    rt.flush_tasks()
    rt.assert_log(
        [
            "Task 0 Fired",
            "A",
            "Task 1 Fired",
            "B",
            "Task 2 Fired",
            "C",
            "Task 3 Fired",
            "D",
            "Task 4 Fired",
            "E",
        ]
    )


def test_yielding_continues_in_a_new_task_regardless_of_how_much_time_is_remaining(
    h: PostTaskSchedulerHarness,
    rt: PostTaskMockRuntime,
) -> None:
    shy = h.unstable_should_yield

    def task(_d: bool):
        rt.log("Original Task")
        rt.log(f"shouldYield: {_js_bool(shy())}")
        rt.log("Return a continuation")
        return lambda _d2: rt.log("Continuation Task")

    h.unstable_schedule_callback(unstable_NormalPriority, task)
    rt.assert_log(["Post Task 0 [user-visible]"])
    rt.flush_tasks()
    rt.assert_log(
        [
            "Task 0 Fired",
            "Original Task",
            "shouldYield: false",
            "Return a continuation",
            "Yield 1 [user-visible]",
        ]
    )
    assert h.unstable_now() == 0
    rt.flush_tasks()
    rt.assert_log(["Task 1 Fired", "Continuation Task"])


@pytest.fixture()
def rt_no_yield() -> PostTaskMockRuntime:
    r = PostTaskMockRuntime()
    r.remove_yield()
    return r


@pytest.fixture()
def h_no_yield(rt_no_yield: PostTaskMockRuntime) -> PostTaskSchedulerHarness:
    return PostTaskSchedulerHarness(rt_no_yield)


def test_falls_back_task_with_continuation(
    h_no_yield: PostTaskSchedulerHarness,
    rt_no_yield: PostTaskMockRuntime,
) -> None:
    rt = rt_no_yield
    h = h_no_yield
    shy = h.unstable_should_yield

    def task(_d: bool):
        rt.log("A")
        while not shy():
            rt.advance_time(1)
        rt.log(f"Yield at {int(h.unstable_now())}ms")
        return lambda _d2: rt.log("Continuation")

    h.unstable_schedule_callback(unstable_NormalPriority, task)
    rt.assert_log(["Post Task 0 [user-visible]"])
    rt.flush_tasks()
    rt.assert_log(
        [
            "Task 0 Fired",
            "A",
            "Yield at 5ms",
            "Post Task 1 [user-visible]",
        ]
    )
    rt.flush_tasks()
    rt.assert_log(["Task 1 Fired", "Continuation"])


def test_falls_back_yielding_continues_in_a_new_task_regardless_of_how_much_time_is_remaining(
    h_no_yield: PostTaskSchedulerHarness,
    rt_no_yield: PostTaskMockRuntime,
) -> None:
    rt = rt_no_yield
    h = h_no_yield
    shy = h.unstable_should_yield

    def task(_d: bool):
        rt.log("Original Task")
        rt.log(f"shouldYield: {_js_bool(shy())}")
        rt.log("Return a continuation")
        return lambda _d2: rt.log("Continuation Task")

    h.unstable_schedule_callback(unstable_NormalPriority, task)
    rt.assert_log(["Post Task 0 [user-visible]"])
    rt.flush_tasks()
    rt.assert_log(
        [
            "Task 0 Fired",
            "Original Task",
            "shouldYield: false",
            "Return a continuation",
            "Post Task 1 [user-visible]",
        ]
    )
    assert h.unstable_now() == 0
    rt.flush_tasks()
    rt.assert_log(["Task 1 Fired", "Continuation Task"])
