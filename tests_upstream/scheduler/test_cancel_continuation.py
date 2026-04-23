from __future__ import annotations

from collections.abc import Callable

from ryact_testkit import FakeTimers
from schedulyr import NORMAL_PRIORITY, Scheduler


def test_cancel_skips_task_before_run() -> None:
    timers = FakeTimers()
    sched = Scheduler(now=timers.now_seconds)
    seen: list[str] = []

    sched.schedule_callback(NORMAL_PRIORITY, lambda: seen.append("a"), delay_ms=0)
    t2 = sched.schedule_callback(NORMAL_PRIORITY, lambda: seen.append("b"), delay_ms=0)
    sched.cancel_callback(t2)

    sched.run_until_idle()
    assert seen == ["a"]


def test_cancel_unknown_id_is_noop() -> None:
    timers = FakeTimers()
    sched = Scheduler(now=timers.now_seconds)
    seen: list[str] = []

    sched.schedule_callback(NORMAL_PRIORITY, lambda: seen.append("a"), delay_ms=0)
    sched.cancel_callback(99999)
    sched.run_until_idle()
    assert seen == ["a"]


def test_cancel_after_run_is_noop() -> None:
    timers = FakeTimers()
    sched = Scheduler(now=timers.now_seconds)
    seen: list[str] = []

    t = sched.schedule_callback(NORMAL_PRIORITY, lambda: seen.append("a"), delay_ms=0)
    sched.run_until_idle()
    assert seen == ["a"]
    sched.cancel_callback(t)
    sched.run_until_idle()
    assert seen == ["a"]


def test_callback_returning_callable_queues_continuation() -> None:
    timers = FakeTimers()
    sched = Scheduler(now=timers.now_seconds)
    seen: list[str] = []

    def step2() -> None:
        seen.append("two")

    def step1() -> Callable[[], None]:
        seen.append("one")
        return step2

    sched.schedule_callback(NORMAL_PRIORITY, step1, delay_ms=0)
    sched.run_until_idle()
    assert seen == ["one", "two"]


def test_three_step_continuation_chain() -> None:
    timers = FakeTimers()
    sched = Scheduler(now=timers.now_seconds)
    seen: list[str] = []

    def step3() -> None:
        seen.append("c")

    def step2() -> Callable[[], None]:
        seen.append("b")
        return step3

    def step1() -> Callable[[], Callable[[], None]]:
        seen.append("a")
        return step2

    sched.schedule_callback(NORMAL_PRIORITY, step1, delay_ms=0)
    sched.run_until_idle()
    assert seen == ["a", "b", "c"]
