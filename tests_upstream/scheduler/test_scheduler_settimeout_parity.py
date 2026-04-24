"""
Parity with ``SchedulerNoDOM`` + ``does not crash non-node SSR`` in ``SchedulerSetTimeout-test.js``.
"""

from __future__ import annotations

import pytest
from ryact_testkit import FakeTimers
from schedulyr import Scheduler
from schedulyr.set_timeout_scheduler import (
    SetTimeoutSchedulerHarness,
    unstable_ImmediatePriority,
    unstable_NormalPriority,
    unstable_UserBlockingPriority,
)


@pytest.fixture()
def timers() -> FakeTimers:
    return FakeTimers()


@pytest.fixture()
def h(timers: FakeTimers) -> SetTimeoutSchedulerHarness:
    return SetTimeoutSchedulerHarness(
        timers.set_timeout,
        timers.now_seconds,
    )


def test_run_all_timers_flushes_all_scheduled_callbacks(
    h: SetTimeoutSchedulerHarness,
    timers: FakeTimers,
) -> None:
    log: list[str] = []
    h.unstable_schedule_callback(unstable_NormalPriority, lambda _d: log.append("A"))
    h.unstable_schedule_callback(unstable_NormalPriority, lambda _d: log.append("B"))
    h.unstable_schedule_callback(unstable_NormalPriority, lambda _d: log.append("C"))
    assert log == []
    timers.run_all_pending()
    assert log == ["A", "B", "C"]


def test_executes_callbacks_in_order_of_priority(
    h: SetTimeoutSchedulerHarness,
    timers: FakeTimers,
) -> None:
    log: list[str] = []
    h.unstable_schedule_callback(unstable_NormalPriority, lambda _d: log.append("A"))
    h.unstable_schedule_callback(unstable_NormalPriority, lambda _d: log.append("B"))
    h.unstable_schedule_callback(unstable_UserBlockingPriority, lambda _d: log.append("C"))
    h.unstable_schedule_callback(unstable_UserBlockingPriority, lambda _d: log.append("D"))
    assert log == []
    timers.run_all_pending()
    assert log == ["C", "D", "A", "B"]


def test_handles_errors(h: SetTimeoutSchedulerHarness, timers: FakeTimers) -> None:
    log: list[str] = []

    def a(_d: bool) -> None:
        log.append("A")
        raise RuntimeError("Oops A")

    def c(_d: bool) -> None:
        log.append("C")
        raise RuntimeError("Oops C")

    h.unstable_schedule_callback(unstable_ImmediatePriority, a)
    h.unstable_schedule_callback(unstable_ImmediatePriority, lambda _d: log.append("B"))
    h.unstable_schedule_callback(unstable_ImmediatePriority, c)
    with pytest.raises(RuntimeError, match="Oops A"):
        timers.run_all_pending()
    assert log == ["A"]
    with pytest.raises(RuntimeError, match="Oops C"):
        timers.run_all_pending()
    assert log == ["A", "B", "C"]


def test_if_settimeout_is_undefined_import_still_works() -> None:
    """``schedulyr`` does not read ``setTimeout`` at import (SSR-safe)."""
    import schedulyr

    assert schedulyr.Scheduler is not None


def test_if_cleartimeout_is_undefined_scheduler_constructible() -> None:
    """Heap ``Scheduler`` does not require ``clearTimeout`` (timer host is injectable)."""
    s = Scheduler()
    assert s is not None
