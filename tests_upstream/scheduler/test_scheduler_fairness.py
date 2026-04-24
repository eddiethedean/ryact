"""
Milestone 15 — cooperative drain cap (synthetic Parity C).

Contract: ``SCHEDULER_FAIRNESS_CONTRACT.md``.
"""

from __future__ import annotations

import pytest
from ryact_testkit import FakeTimers
from schedulyr import NORMAL_PRIORITY, Scheduler


def test_max_tasks_negative_raises() -> None:
    timers = FakeTimers()
    sched = Scheduler(now=timers.now_seconds)
    sched.schedule_callback(NORMAL_PRIORITY, lambda: None, delay_ms=0)
    with pytest.raises(ValueError, match="max_tasks"):
        sched.run_until_idle(max_tasks=-1)


def test_max_tasks_splits_three_callbacks_across_drains() -> None:
    timers = FakeTimers()
    sched = Scheduler(now=timers.now_seconds)
    seen: list[str] = []

    sched.schedule_callback(NORMAL_PRIORITY, lambda: seen.append("a"), delay_ms=0)
    sched.schedule_callback(NORMAL_PRIORITY, lambda: seen.append("b"), delay_ms=0)
    sched.schedule_callback(NORMAL_PRIORITY, lambda: seen.append("c"), delay_ms=0)

    sched.run_until_idle(max_tasks=2)
    assert seen == ["a", "b"]

    sched.run_until_idle()
    assert seen == ["a", "b", "c"]


def test_max_tasks_zero_runs_no_callbacks() -> None:
    timers = FakeTimers()
    sched = Scheduler(now=timers.now_seconds)
    seen: list[str] = []

    sched.schedule_callback(NORMAL_PRIORITY, lambda: seen.append("x"), delay_ms=0)
    sched.run_until_idle(max_tasks=0)
    assert seen == []

    sched.run_until_idle()
    assert seen == ["x"]


def test_max_tasks_one_stops_before_continuation_body() -> None:
    timers = FakeTimers()
    sched = Scheduler(now=timers.now_seconds)
    seen: list[str] = []

    def cont() -> None:
        seen.append("two")

    def outer():
        seen.append("one")
        return cont

    sched.schedule_callback(NORMAL_PRIORITY, outer, delay_ms=0)
    sched.run_until_idle(max_tasks=1)
    assert seen == ["one"]

    sched.run_until_idle()
    assert seen == ["one", "two"]


def test_max_tasks_and_time_slice_both_apply() -> None:
    timers = FakeTimers()
    sched = Scheduler(now=timers.now_seconds)
    seen: list[str] = []

    def slow() -> None:
        seen.append("slow")
        timers.advance(5)

    sched.schedule_callback(NORMAL_PRIORITY, slow, delay_ms=0)
    sched.schedule_callback(NORMAL_PRIORITY, lambda: seen.append("fast"), delay_ms=0)

    sched.run_until_idle(time_slice_ms=1, max_tasks=10)
    assert seen == ["slow"]

    sched.run_until_idle()
    assert seen == ["slow", "fast"]


def test_cancelled_head_does_not_count_toward_max_tasks() -> None:
    timers = FakeTimers()
    sched = Scheduler(now=timers.now_seconds)
    seen: list[str] = []

    t_cancel = sched.schedule_callback(NORMAL_PRIORITY, lambda: seen.append("bad"), delay_ms=0)
    sched.schedule_callback(NORMAL_PRIORITY, lambda: seen.append("good"), delay_ms=0)
    sched.cancel_callback(t_cancel)

    sched.run_until_idle(max_tasks=1)
    assert seen == ["good"]
