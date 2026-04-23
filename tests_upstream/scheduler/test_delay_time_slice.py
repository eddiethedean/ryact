from __future__ import annotations

from ryact_testkit import FakeTimers
from schedulyr import NORMAL_PRIORITY, Scheduler


def test_earlier_due_runs_first_with_same_priority() -> None:
    timers = FakeTimers()
    sched = Scheduler(now=timers.now_seconds)
    seen: list[str] = []

    sched.schedule_callback(NORMAL_PRIORITY, lambda: seen.append("late"), delay_ms=50)
    sched.schedule_callback(NORMAL_PRIORITY, lambda: seen.append("early"), delay_ms=10)

    sched.run_until_idle()
    assert seen == []

    timers.advance(10)
    sched.run_until_idle()
    assert seen == ["early"]

    timers.advance(40)
    sched.run_until_idle()
    assert seen == ["early", "late"]


def test_negative_delay_ms_clamped_to_immediate() -> None:
    timers = FakeTimers()
    sched = Scheduler(now=timers.now_seconds)
    seen: list[str] = []

    sched.schedule_callback(NORMAL_PRIORITY, lambda: seen.append("a"), delay_ms=-100)
    sched.run_until_idle()
    assert seen == ["a"]


def test_time_slice_zero_runs_no_callbacks() -> None:
    timers = FakeTimers()
    sched = Scheduler(now=timers.now_seconds)
    seen: list[str] = []

    sched.schedule_callback(NORMAL_PRIORITY, lambda: seen.append("x"), delay_ms=0)
    sched.run_until_idle(time_slice_ms=0)
    assert seen == []


def test_time_slice_yields_after_callback_advances_time() -> None:
    timers = FakeTimers()
    sched = Scheduler(now=timers.now_seconds)
    seen: list[str] = []

    def first() -> None:
        seen.append("first")
        timers.advance(2)

    sched.schedule_callback(NORMAL_PRIORITY, first, delay_ms=0)
    sched.schedule_callback(NORMAL_PRIORITY, lambda: seen.append("second"), delay_ms=0)

    sched.run_until_idle(time_slice_ms=1)
    assert seen == ["first"]

    sched.run_until_idle()
    assert seen == ["first", "second"]
