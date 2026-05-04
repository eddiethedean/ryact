from __future__ import annotations

from schedulyr import Scheduler


def test_scheduler_run_until_idle_time_slicing_cap() -> None:
    # Minimal acceptance slice for SchedulerIntegration work:
    # run_until_idle can be capped by max_tasks deterministically.
    sched = Scheduler()
    seen: list[int] = []
    for i in range(5):
        sched.schedule_callback(3, lambda i=i: seen.append(i))
    sched.run_until_idle(max_tasks=2)
    assert len(seen) == 2
    sched.run_until_idle()
    assert len(seen) == 5

