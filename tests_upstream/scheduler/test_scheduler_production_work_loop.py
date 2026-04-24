"""
Parity C (Milestone 14): ``Scheduler`` work-loop invariants aligned with React
``Scheduler.js`` (timer vs task heaps, expiration ordering).

These tests lock behavior beyond the legacy heap manifest rows; they should fail
if ``schedulyr.scheduler.Scheduler`` regresses to a single ``(due, priority, id)`` heap
without matching promotion and expiration semantics.
"""

from __future__ import annotations

from ryact_testkit import FakeTimers
from schedulyr import (
    IMMEDIATE_PRIORITY,
    NORMAL_PRIORITY,
    Scheduler,
)


def test_delayed_mixed_priority_runs_higher_urgency_first_when_timers_fire() -> None:
    """After the same delay, expiration ordering matches React (Immediate before Normal)."""
    timers = FakeTimers()
    sched = Scheduler(now=timers.now_seconds)
    seen: list[str] = []

    sched.schedule_callback(NORMAL_PRIORITY, lambda: seen.append("n"), delay_ms=10)
    sched.schedule_callback(IMMEDIATE_PRIORITY, lambda: seen.append("i"), delay_ms=10)

    timers.advance(10)
    sched.run_until_idle()
    assert seen == ["i", "n"]


def test_same_priority_delayed_fifo_when_timers_fire_together() -> None:
    timers = FakeTimers()
    sched = Scheduler(now=timers.now_seconds)
    seen: list[str] = []

    sched.schedule_callback(NORMAL_PRIORITY, lambda: seen.append("first"), delay_ms=5)
    sched.schedule_callback(NORMAL_PRIORITY, lambda: seen.append("second"), delay_ms=5)

    timers.advance(5)
    sched.run_until_idle()
    assert seen == ["first", "second"]


def test_timer_promotes_before_running_later_start_time() -> None:
    """Smaller ``start_time`` is promoted first; later delay runs after advance."""
    timers = FakeTimers()
    sched = Scheduler(now=timers.now_seconds)
    seen: list[str] = []

    sched.schedule_callback(NORMAL_PRIORITY, lambda: seen.append("late"), delay_ms=30)
    sched.schedule_callback(NORMAL_PRIORITY, lambda: seen.append("early"), delay_ms=10)

    timers.advance(10)
    sched.run_until_idle()
    assert seen == ["early"]

    timers.advance(20)
    sched.run_until_idle()
    assert seen == ["early", "late"]
