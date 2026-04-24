from __future__ import annotations

import pytest


def _hypothesis() -> object:
    try:
        import hypothesis  # noqa: F401
        from hypothesis import given, settings  # type: ignore
        from hypothesis import strategies as st  # type: ignore

        return given, settings, st
    except Exception:  # pragma: no cover
        pytest.skip(
            "hypothesis not installed (optional M17 property tests)",
            allow_module_level=True,
        )


from ryact_testkit import FakeTimers  # noqa: E402
from schedulyr import IMMEDIATE_PRIORITY, NORMAL_PRIORITY, Scheduler  # noqa: E402

given, settings, st = _hypothesis()  # type: ignore[misc]


@settings(max_examples=50, deadline=None)
@given(st.integers(min_value=1, max_value=50))
def test_cancelled_tasks_never_run(n: int) -> None:
    ran: list[int] = []
    timers = FakeTimers()
    s = Scheduler(now=timers.now)
    ids = []
    for i in range(n):
        tid = s.schedule_callback(NORMAL_PRIORITY, lambda i=i: ran.append(i), delay_ms=0)
        ids.append(tid)

    # Cancel a prefix; the remainder should still run.
    cancel_upto = n // 2
    for tid in ids[:cancel_upto]:
        s.cancel_callback(tid)

    s.run_until_idle()

    assert all(i not in ran for i in range(cancel_upto))
    assert sorted(ran) == list(range(cancel_upto, n))


@settings(max_examples=50, deadline=None)
@given(st.integers(min_value=1, max_value=50))
def test_fifo_for_equal_priority_immediate_tasks(n: int) -> None:
    timers = FakeTimers()
    s = Scheduler(now=timers.now)

    order: list[int] = []
    for idx in range(n):
        s.schedule_callback(NORMAL_PRIORITY, lambda idx=idx: order.append(idx), delay_ms=0)
    s.run_until_idle()

    assert order == list(range(n))


def test_continuation_runs_after_initial_callback() -> None:
    timers = FakeTimers()
    s = Scheduler(now=timers.now)
    log: list[str] = []

    def first() -> object:
        log.append("first")

        def cont() -> None:
            log.append("cont")

        return cont

    s.schedule_callback(IMMEDIATE_PRIORITY, first, delay_ms=0)
    s.run_until_idle()
    assert log == ["first", "cont"]

