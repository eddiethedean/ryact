from __future__ import annotations

from ryact_testkit import FakeTimers
from schedulyr import NORMAL_PRIORITY, Scheduler


def test_scheduler_runs_delayed_work_deterministically() -> None:
    timers = FakeTimers()
    sched = Scheduler(now=timers.now_seconds)
    seen = []

    sched.schedule_callback(NORMAL_PRIORITY, lambda: seen.append("a"), delay_ms=10)
    sched.run_until_idle()
    assert seen == []

    timers.advance(10)
    sched.run_until_idle()
    assert seen == ["a"]
