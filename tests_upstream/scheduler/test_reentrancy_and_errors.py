"""
Re-entrant scheduling, continuation interaction, cancellation from callbacks,
and error propagation (Milestone 2).

Continuation vs nested schedule: work scheduled during a callback is heappushed
before the continuation returned from that callback is enqueued, so among
equal (due, priority), nested work runs before the continuation (lower task id).
"""

from __future__ import annotations

import pytest
from ryact_testkit import FakeTimers
from schedulyr import (
    IMMEDIATE_PRIORITY,
    LOW_PRIORITY,
    NORMAL_PRIORITY,
    Scheduler,
)


def test_nested_schedule_respects_priority_order() -> None:
    timers = FakeTimers()
    sched = Scheduler(now=timers.now_seconds)
    seen: list[str] = []

    def a() -> None:
        seen.append("A")
        sched.schedule_callback(IMMEDIATE_PRIORITY, lambda: seen.append("B"), delay_ms=0)
        sched.schedule_callback(LOW_PRIORITY, lambda: seen.append("C"), delay_ms=0)

    sched.schedule_callback(NORMAL_PRIORITY, a, delay_ms=0)
    sched.run_until_idle()
    assert seen == ["A", "B", "C"]


def test_nested_work_runs_before_continuation_same_priority() -> None:
    """B is pushed during A; continuation A2 is pushed after A returns — lower id wins."""
    timers = FakeTimers()
    sched = Scheduler(now=timers.now_seconds)
    seen: list[str] = []

    def a2() -> None:
        seen.append("A2")

    def a() -> object:
        seen.append("A")
        sched.schedule_callback(NORMAL_PRIORITY, lambda: seen.append("B"), delay_ms=0)
        return a2

    sched.schedule_callback(NORMAL_PRIORITY, a, delay_ms=0)
    sched.run_until_idle()
    assert seen == ["A", "B", "A2"]


def test_cancel_from_callback_prevents_scheduled_task() -> None:
    timers = FakeTimers()
    sched = Scheduler(now=timers.now_seconds)
    seen: list[str] = []

    def a() -> None:
        seen.append("A")
        tb = sched.schedule_callback(NORMAL_PRIORITY, lambda: seen.append("B"), delay_ms=0)
        sched.cancel_callback(tb)

    sched.schedule_callback(NORMAL_PRIORITY, a, delay_ms=0)
    sched.run_until_idle()
    assert seen == ["A"]


def test_multi_level_nested_scheduling() -> None:
    timers = FakeTimers()
    sched = Scheduler(now=timers.now_seconds)
    seen: list[str] = []

    def c() -> None:
        seen.append("C")

    def b() -> None:
        seen.append("B")
        sched.schedule_callback(NORMAL_PRIORITY, c, delay_ms=0)

    def a() -> None:
        seen.append("A")
        sched.schedule_callback(NORMAL_PRIORITY, b, delay_ms=0)

    sched.schedule_callback(NORMAL_PRIORITY, a, delay_ms=0)
    sched.run_until_idle()
    assert seen == ["A", "B", "C"]


def test_callback_exception_propagates_remaining_tasks_stay_queued() -> None:
    timers = FakeTimers()
    sched = Scheduler(now=timers.now_seconds)
    seen: list[str] = []

    def bad() -> None:
        raise ValueError("boom")

    def good() -> None:
        seen.append("ok")

    sched.schedule_callback(NORMAL_PRIORITY, bad, delay_ms=0)
    sched.schedule_callback(NORMAL_PRIORITY, good, delay_ms=0)

    with pytest.raises(ValueError, match="boom"):
        sched.run_until_idle()
    assert seen == []

    sched.run_until_idle()
    assert seen == ["ok"]


def test_continuation_that_raises_propagates() -> None:
    timers = FakeTimers()
    sched = Scheduler(now=timers.now_seconds)

    def cont() -> None:
        raise RuntimeError("continuation failed")

    def outer() -> object:
        return cont

    sched.schedule_callback(NORMAL_PRIORITY, outer, delay_ms=0)
    with pytest.raises(RuntimeError, match="continuation failed"):
        sched.run_until_idle()
