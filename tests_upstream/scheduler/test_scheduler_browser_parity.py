"""
Parity with ``SchedulerBrowser`` in ``packages/scheduler/src/__tests__/Scheduler-test.js``.

Uses :class:`schedulyr.mock_browser_runtime.MockBrowserRuntime` and
:class:`schedulyr.browser_scheduler.BrowserSchedulerHarness`.
"""

from __future__ import annotations

import pytest
from schedulyr import (
    BrowserSchedulerHarness,
    MockBrowserRuntime,
    SchedulerBrowserFlags,
    unstable_NormalPriority,
)


@pytest.fixture()
def flags() -> SchedulerBrowserFlags:
    """Stable OSS defaults (``enableAlwaysYieldScheduler`` false, ``enableRequestPaint`` true)."""
    return SchedulerBrowserFlags()


def test_task_that_finishes_before_deadline(flags: SchedulerBrowserFlags) -> None:
    rt = MockBrowserRuntime()
    h = BrowserSchedulerHarness(rt, flags)

    def task(_did: bool) -> None:
        rt.log("Task")

    h.unstable_schedule_callback(unstable_NormalPriority, task)
    rt.assert_log(["Post Message"])
    rt.fire_message_event()
    rt.assert_log(["Message Event", "Task"])


def test_task_with_continuation(flags: SchedulerBrowserFlags) -> None:
    rt = MockBrowserRuntime()
    h = BrowserSchedulerHarness(rt, flags)

    def task(_did: bool):
        rt.log("Task")
        h.unstable_request_paint()
        while not h.unstable_should_yield():
            rt.advance_time(1)
        rt.log(f"Yield at {int(h.unstable_now())}ms")
        return lambda _d: rt.log("Continuation")

    h.unstable_schedule_callback(unstable_NormalPriority, task)
    rt.assert_log(["Post Message"])
    rt.fire_message_event()
    if flags.gate(lambda f: f.enable_always_yield_scheduler) or (not flags.enable_request_paint):
        exp_yield = "Yield at 10ms" if flags.gate(lambda f: f.www) else "Yield at 5ms"
    else:
        exp_yield = "Yield at 0ms"
    rt.assert_log(["Message Event", "Task", exp_yield, "Post Message"])
    rt.fire_message_event()
    rt.assert_log(["Message Event", "Continuation"])


def test_multiple_tasks(flags: SchedulerBrowserFlags) -> None:
    rt = MockBrowserRuntime()
    h = BrowserSchedulerHarness(rt, flags)

    h.unstable_schedule_callback(unstable_NormalPriority, lambda _d: rt.log("A"))
    h.unstable_schedule_callback(unstable_NormalPriority, lambda _d: rt.log("B"))
    rt.assert_log(["Post Message"])
    rt.fire_message_event()
    if flags.gate(lambda f: f.enable_always_yield_scheduler):
        rt.assert_log(["Message Event", "A", "Post Message"])
        rt.fire_message_event()
        rt.assert_log(["Message Event", "B"])
    else:
        rt.assert_log(["Message Event", "A", "B"])


def test_multiple_tasks_with_a_yield_in_between(flags: SchedulerBrowserFlags) -> None:
    rt = MockBrowserRuntime()
    h = BrowserSchedulerHarness(rt, flags)

    def a(_did: bool) -> None:
        rt.log("A")
        rt.advance_time(4999)

    h.unstable_schedule_callback(unstable_NormalPriority, a)
    h.unstable_schedule_callback(unstable_NormalPriority, lambda _d: rt.log("B"))
    rt.assert_log(["Post Message"])
    rt.fire_message_event()
    rt.assert_log(
        [
            "Message Event",
            "A",
            "Post Message",
        ]
    )
    rt.fire_message_event()
    rt.assert_log(["Message Event", "B"])


def test_cancels_tasks(flags: SchedulerBrowserFlags) -> None:
    rt = MockBrowserRuntime()
    h = BrowserSchedulerHarness(rt, flags)

    handle = h.unstable_schedule_callback(unstable_NormalPriority, lambda _d: rt.log("Task"))
    rt.assert_log(["Post Message"])
    h.unstable_cancel_callback(handle)
    rt.fire_message_event()
    rt.assert_log(["Message Event"])


def test_throws_when_task_errors_then_continues(flags: SchedulerBrowserFlags) -> None:
    rt = MockBrowserRuntime()
    h = BrowserSchedulerHarness(rt, flags)

    def oops(_did: bool) -> None:
        rt.log("Oops!")
        raise RuntimeError("Oops!")

    h.unstable_schedule_callback(unstable_NormalPriority, oops)
    h.unstable_schedule_callback(unstable_NormalPriority, lambda _d: rt.log("Yay"))
    rt.assert_log(["Post Message"])
    with pytest.raises(RuntimeError, match="Oops!"):
        rt.fire_message_event()
    rt.assert_log(["Message Event", "Oops!", "Post Message"])
    rt.fire_message_event()
    if flags.gate(lambda f: f.enable_always_yield_scheduler):
        rt.assert_log(["Message Event", "Post Message"])
        rt.fire_message_event()
    rt.assert_log(["Message Event", "Yay"])


def test_schedule_new_task_after_queue_has_emptied(flags: SchedulerBrowserFlags) -> None:
    rt = MockBrowserRuntime()
    h = BrowserSchedulerHarness(rt, flags)

    h.unstable_schedule_callback(unstable_NormalPriority, lambda _d: rt.log("A"))
    rt.assert_log(["Post Message"])
    rt.fire_message_event()
    rt.assert_log(["Message Event", "A"])
    h.unstable_schedule_callback(unstable_NormalPriority, lambda _d: rt.log("B"))
    rt.assert_log(["Post Message"])
    rt.fire_message_event()
    rt.assert_log(["Message Event", "B"])


def test_schedule_new_task_after_a_cancellation(flags: SchedulerBrowserFlags) -> None:
    rt = MockBrowserRuntime()
    h = BrowserSchedulerHarness(rt, flags)

    handle = h.unstable_schedule_callback(unstable_NormalPriority, lambda _d: rt.log("A"))
    rt.assert_log(["Post Message"])
    h.unstable_cancel_callback(handle)
    rt.fire_message_event()
    rt.assert_log(["Message Event"])
    h.unstable_schedule_callback(unstable_NormalPriority, lambda _d: rt.log("B"))
    rt.assert_log(["Post Message"])
    rt.fire_message_event()
    rt.assert_log(["Message Event", "B"])


def test_yielding_continues_in_new_task(flags: SchedulerBrowserFlags) -> None:
    rt = MockBrowserRuntime()
    h = BrowserSchedulerHarness(rt, flags)

    def work(_did: bool):
        rt.log("Original Task")
        rt.log("shouldYield: " + str(h.unstable_should_yield()).lower())
        rt.log("Return a continuation")
        return lambda _d: rt.log("Continuation Task")

    h.unstable_schedule_callback(unstable_NormalPriority, work)
    rt.assert_log(["Post Message"])
    rt.fire_message_event()
    rt.assert_log(
        [
            "Message Event",
            "Original Task",
            "shouldYield: false",
            "Return a continuation",
            "Post Message",
        ]
    )
    assert h.unstable_now() == 0
    rt.fire_message_event()
    rt.assert_log(["Message Event", "Continuation Task"])
