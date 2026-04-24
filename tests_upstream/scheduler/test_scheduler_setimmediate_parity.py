"""
Parity with ``SchedulerDOMSetImmediate`` + top-level test in ``SchedulerSetImmediate-test.js``.
"""

from __future__ import annotations

import pytest
from schedulyr.browser_scheduler import SchedulerBrowserFlags
from schedulyr.set_immediate_runtime import SetImmediateMockRuntime
from schedulyr.set_immediate_scheduler import (
    SetImmediateSchedulerHarness,
    unstable_NormalPriority,
    unstable_UserBlockingPriority,
)


@pytest.fixture()
def rt() -> SetImmediateMockRuntime:
    return SetImmediateMockRuntime()


@pytest.fixture()
def flags() -> SchedulerBrowserFlags:
    return SchedulerBrowserFlags()


@pytest.fixture()
def h(rt: SetImmediateMockRuntime, flags: SchedulerBrowserFlags) -> SetImmediateSchedulerHarness:
    return SetImmediateSchedulerHarness(rt, flags)


def test_does_not_use_setimmediate_override(
    rt: SetImmediateMockRuntime,
    flags: SchedulerBrowserFlags,
) -> None:
    h = SetImmediateSchedulerHarness(rt, flags)
    h.unstable_schedule_callback(unstable_NormalPriority, lambda _d: rt.log("Task"))
    rt.assert_log(["Set Immediate"])
    rt.fire_immediate()
    rt.assert_log(["setImmediate Callback", "Task"])


def test_task_that_finishes_before_deadline(
    h: SetImmediateSchedulerHarness,
    rt: SetImmediateMockRuntime,
) -> None:
    h.unstable_schedule_callback(unstable_NormalPriority, lambda _d: rt.log("Task"))
    rt.assert_log(["Set Immediate"])
    rt.fire_immediate()
    rt.assert_log(["setImmediate Callback", "Task"])


def test_task_with_continuation(
    h: SetImmediateSchedulerHarness,
    rt: SetImmediateMockRuntime,
) -> None:
    flags = h._flags

    def task(_d: bool):
        rt.log("Task")
        while not h.unstable_should_yield():
            rt.advance_time(1)
        rt.log("Yield at 10ms" if flags.gate(lambda f: f.www) else "Yield at 5ms")
        return lambda _d2: rt.log("Continuation")

    h.unstable_schedule_callback(unstable_NormalPriority, task)
    rt.assert_log(["Set Immediate"])
    rt.fire_immediate()
    exp_yield = "Yield at 10ms" if flags.gate(lambda f: f.www) else "Yield at 5ms"
    rt.assert_log(
        [
            "setImmediate Callback",
            "Task",
            exp_yield,
            "Set Immediate",
        ]
    )
    rt.fire_immediate()
    rt.assert_log(["setImmediate Callback", "Continuation"])


def test_multiple_tasks(h: SetImmediateSchedulerHarness, rt: SetImmediateMockRuntime) -> None:
    flags = h._flags
    h.unstable_schedule_callback(unstable_NormalPriority, lambda _d: rt.log("A"))
    h.unstable_schedule_callback(unstable_NormalPriority, lambda _d: rt.log("B"))
    rt.assert_log(["Set Immediate"])
    rt.fire_immediate()
    if flags.gate(lambda f: f.enable_always_yield_scheduler):
        rt.assert_log(["setImmediate Callback", "A", "Set Immediate"])
        rt.fire_immediate()
        rt.assert_log(["setImmediate Callback", "B"])
    else:
        rt.assert_log(["setImmediate Callback", "A", "B"])


def test_multiple_tasks_at_different_priority(
    h: SetImmediateSchedulerHarness,
    rt: SetImmediateMockRuntime,
) -> None:
    flags = h._flags
    h.unstable_schedule_callback(unstable_NormalPriority, lambda _d: rt.log("A"))
    h.unstable_schedule_callback(unstable_UserBlockingPriority, lambda _d: rt.log("B"))
    rt.assert_log(["Set Immediate"])
    rt.fire_immediate()
    if flags.gate(lambda f: f.enable_always_yield_scheduler):
        rt.assert_log(["setImmediate Callback", "B", "Set Immediate"])
        rt.fire_immediate()
        rt.assert_log(["setImmediate Callback", "A"])
    else:
        rt.assert_log(["setImmediate Callback", "B", "A"])


def test_multiple_tasks_with_a_yield_in_between(
    h: SetImmediateSchedulerHarness,
    rt: SetImmediateMockRuntime,
) -> None:
    h.unstable_schedule_callback(
        unstable_NormalPriority,
        lambda _d: rt.log("A") or rt.advance_time(4999),
    )
    h.unstable_schedule_callback(unstable_NormalPriority, lambda _d: rt.log("B"))
    rt.assert_log(["Set Immediate"])
    rt.fire_immediate()
    rt.assert_log(
        [
            "setImmediate Callback",
            "A",
            "Set Immediate",
        ]
    )
    rt.fire_immediate()
    rt.assert_log(["setImmediate Callback", "B"])


def test_cancels_tasks(h: SetImmediateSchedulerHarness, rt: SetImmediateMockRuntime) -> None:
    t = h.unstable_schedule_callback(unstable_NormalPriority, lambda _d: rt.log("Task"))
    rt.assert_log(["Set Immediate"])
    h.unstable_cancel_callback(t)
    rt.assert_log([])


def test_throws_when_a_task_errors_then_continues_in_a_new_event(
    h: SetImmediateSchedulerHarness,
    rt: SetImmediateMockRuntime,
) -> None:
    flags = h._flags
    def oops(_d: bool) -> None:
        rt.log("Oops!")
        raise RuntimeError("Oops!")

    h.unstable_schedule_callback(unstable_NormalPriority, oops)
    h.unstable_schedule_callback(unstable_NormalPriority, lambda _d: rt.log("Yay"))
    rt.assert_log(["Set Immediate"])
    with pytest.raises(RuntimeError, match="Oops!"):
        rt.fire_immediate()
    rt.assert_log(["setImmediate Callback", "Oops!", "Set Immediate"])
    rt.fire_immediate()
    if flags.gate(lambda f: f.enable_always_yield_scheduler):
        rt.assert_log(["setImmediate Callback", "Set Immediate"])
        rt.fire_immediate()
        rt.assert_log(["setImmediate Callback", "Yay"])
    else:
        rt.assert_log(["setImmediate Callback", "Yay"])


def test_schedule_new_task_after_queue_has_emptied(
    h: SetImmediateSchedulerHarness,
    rt: SetImmediateMockRuntime,
) -> None:
    h.unstable_schedule_callback(unstable_NormalPriority, lambda _d: rt.log("A"))
    rt.assert_log(["Set Immediate"])
    rt.fire_immediate()
    rt.assert_log(["setImmediate Callback", "A"])
    h.unstable_schedule_callback(unstable_NormalPriority, lambda _d: rt.log("B"))
    rt.assert_log(["Set Immediate"])
    rt.fire_immediate()
    rt.assert_log(["setImmediate Callback", "B"])


def test_schedule_new_task_after_a_cancellation(
    h: SetImmediateSchedulerHarness,
    rt: SetImmediateMockRuntime,
) -> None:
    handle = h.unstable_schedule_callback(unstable_NormalPriority, lambda _d: rt.log("A"))
    rt.assert_log(["Set Immediate"])
    h.unstable_cancel_callback(handle)
    rt.fire_immediate()
    rt.assert_log(["setImmediate Callback"])
    h.unstable_schedule_callback(unstable_NormalPriority, lambda _d: rt.log("B"))
    rt.assert_log(["Set Immediate"])
    rt.fire_immediate()
    rt.assert_log(["setImmediate Callback", "B"])


def test_does_not_crash_if_setimmediate_is_undefined() -> None:
    """``schedulyr`` does not require ``setImmediate`` at import (unlike Node scheduler bundle)."""
    import schedulyr

    assert schedulyr.Scheduler is not None
