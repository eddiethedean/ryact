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


@pytest.fixture()
def rt() -> PostTaskMockRuntime:
    r = PostTaskMockRuntime()
    r.wire_default_yield()
    return r


@pytest.fixture()
def h(rt: PostTaskMockRuntime) -> PostTaskSchedulerHarness:
    return PostTaskSchedulerHarness(rt)


def test_current_priority_is_set_during_task_and_resets_after(
    h: PostTaskSchedulerHarness, rt: PostTaskMockRuntime
) -> None:
    assert h.unstable_get_current_priority_level() == unstable_NormalPriority

    def task(_d: bool) -> None:
        assert h.unstable_get_current_priority_level() == unstable_UserBlockingPriority
        rt.log("A")

    h.unstable_schedule_callback(unstable_UserBlockingPriority, task)
    rt.assert_log(["Post Task 0 [user-blocking]"])
    rt.flush_tasks()
    rt.assert_log(["Task 0 Fired", "A"])

    assert h.unstable_get_current_priority_level() == unstable_NormalPriority


def test_run_with_priority_sets_and_restores(h: PostTaskSchedulerHarness) -> None:
    assert h.unstable_get_current_priority_level() == unstable_NormalPriority
    seen: list[int] = []

    def inner() -> None:
        seen.append(h.unstable_get_current_priority_level())

    h.unstable_run_with_priority(
        unstable_UserBlockingPriority,
        lambda: h.unstable_run_with_priority(unstable_ImmediatePriority, inner),
    )
    assert seen == [unstable_ImmediatePriority]
    assert h.unstable_get_current_priority_level() == unstable_NormalPriority


def test_next_shifts_high_priorities_down_to_normal(h: PostTaskSchedulerHarness) -> None:
    seen: list[int] = []

    def record() -> None:
        seen.append(h.unstable_get_current_priority_level())

    h.unstable_run_with_priority(unstable_ImmediatePriority, lambda: h.unstable_next(record))
    h.unstable_run_with_priority(unstable_UserBlockingPriority, lambda: h.unstable_next(record))
    h.unstable_run_with_priority(unstable_NormalPriority, lambda: h.unstable_next(record))
    assert seen == [unstable_NormalPriority, unstable_NormalPriority, unstable_NormalPriority]


def test_next_keeps_low_and_idle_priorities(h: PostTaskSchedulerHarness) -> None:
    seen: list[int] = []

    def record() -> None:
        seen.append(h.unstable_get_current_priority_level())

    h.unstable_run_with_priority(unstable_LowPriority, lambda: h.unstable_next(record))
    h.unstable_run_with_priority(unstable_IdlePriority, lambda: h.unstable_next(record))
    assert seen == [unstable_LowPriority, unstable_IdlePriority]


def test_wrap_callback_captures_parent_priority(h: PostTaskSchedulerHarness) -> None:
    seen: list[int] = []

    def cb() -> None:
        seen.append(h.unstable_get_current_priority_level())

    def outer() -> None:
        wrapped = h.unstable_wrap_callback(cb)
        h.unstable_run_with_priority(unstable_ImmediatePriority, wrapped)

    h.unstable_run_with_priority(unstable_UserBlockingPriority, outer)
    assert seen == [unstable_UserBlockingPriority]


def test_continuation_runs_with_task_priority_and_resets_after(
    h: PostTaskSchedulerHarness, rt: PostTaskMockRuntime
) -> None:
    seen: list[int] = []

    def first(_d: bool):
        seen.append(h.unstable_get_current_priority_level())

        def cont(_d2: bool) -> None:
            seen.append(h.unstable_get_current_priority_level())
            rt.log("C")

        return cont

    h.unstable_schedule_callback(unstable_UserBlockingPriority, first)
    rt.assert_log(["Post Task 0 [user-blocking]"])
    rt.flush_tasks()
    # With yield present, continuations are scheduled as `Yield ...` ticks.
    rt.assert_log(["Task 0 Fired", "Yield 1 [user-blocking]"])
    assert h.unstable_get_current_priority_level() == unstable_NormalPriority

    rt.flush_tasks()
    rt.assert_log(["Task 1 Fired", "C"])
    assert seen == [unstable_UserBlockingPriority, unstable_UserBlockingPriority]
    assert h.unstable_get_current_priority_level() == unstable_NormalPriority


def test_cancel_aborts_task_and_suppresses_abort_noise(h: PostTaskSchedulerHarness, rt: PostTaskMockRuntime) -> None:
    handle = h.unstable_schedule_callback(unstable_NormalPriority, lambda _d: rt.log("A"))
    rt.assert_log(["Post Task 0 [user-visible]"])
    h.unstable_cancel_callback(handle)
    rt.flush_tasks()
    rt.assert_log([])
