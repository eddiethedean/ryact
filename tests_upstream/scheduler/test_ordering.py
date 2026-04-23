from __future__ import annotations

from ryact_testkit import FakeTimers
from schedulyr import (
    IDLE_PRIORITY,
    IMMEDIATE_PRIORITY,
    NORMAL_PRIORITY,
    Scheduler,
)


def test_lower_numeric_priority_runs_first_when_same_due() -> None:
    timers = FakeTimers()
    sched = Scheduler(now=timers.now_seconds)
    seen: list[str] = []

    sched.schedule_callback(IDLE_PRIORITY, lambda: seen.append("idle"), delay_ms=0)
    sched.schedule_callback(IMMEDIATE_PRIORITY, lambda: seen.append("imm"), delay_ms=0)

    sched.run_until_idle()
    assert seen == ["imm", "idle"]


def test_same_priority_fifo_by_schedule_order() -> None:
    timers = FakeTimers()
    sched = Scheduler(now=timers.now_seconds)
    seen: list[str] = []

    sched.schedule_callback(NORMAL_PRIORITY, lambda: seen.append("first"), delay_ms=0)
    sched.schedule_callback(NORMAL_PRIORITY, lambda: seen.append("second"), delay_ms=0)

    sched.run_until_idle()
    assert seen == ["first", "second"]
