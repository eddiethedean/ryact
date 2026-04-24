from __future__ import annotations

import pytest
import schedulyr.production_scheduler as prod
from schedulyr.scheduler import NORMAL_PRIORITY
from schedulyr.scheduler_profiling_buffer import (
    PROFILING_OVERFLOW_MESSAGE,
    ProfilingEventLogger,
    SchedulerProfilingBuffer,
)

from tests_upstream.scheduler.profiling_flamegraph import stop_profiling_and_print_flamegraph


@pytest.fixture(autouse=True)
def _start_stop_profiling():
    # Reset warnings between tests.
    prod._profiling_warnings.clear()  # noqa: SLF001

    prod.unstable_Profiling.start_logging_profiling_events()
    yield
    # Ensure buffer is reset between tests.
    prod.unstable_Profiling.stop_logging_profiling_events()


def _fg() -> str:
    raw = prod.unstable_Profiling.stop_logging_profiling_events()
    return stop_profiling_and_print_flamegraph(raw)


def test_production_profiling_basic_flamegraph() -> None:
    seen: list[str] = []

    def outer(_d: bool):
        seen.append("Yield 1")

        def inner(_d2: bool):
            seen.append("Yield 2")
            return None

        prod.unstable_schedule_callback(NORMAL_PRIORITY, inner, {"label": "Bar"})
        seen.append("Yield 3")

        def cont(_d3: bool):
            seen.append("Yield 4")
            return None

        return cont

    prod.unstable_schedule_callback(NORMAL_PRIORITY, outer, {"label": "Foo"})
    prod._scheduler.run_until_idle()  # type: ignore[attr-defined]  # noqa: SLF001
    assert seen == ["Yield 1", "Yield 3", "Yield 2", "Yield 4"]

    fg = _fg()
    assert "Main thread" in fg
    assert "Task 1 [Normal]" in fg
    assert "Task 2 [Normal]" in fg


def test_production_profiling_marks_cancel() -> None:
    def task(_d: bool):
        return None

    t = prod.unstable_schedule_callback(NORMAL_PRIORITY, task, {"label": "A"})
    prod.unstable_cancel_callback(t)
    prod._scheduler.run_until_idle()  # type: ignore[attr-defined]  # noqa: SLF001
    fg = _fg()
    assert "canceled" in fg


def test_production_profiling_marks_error() -> None:
    def bad(_d: bool):
        raise RuntimeError("Oops")

    with pytest.raises(RuntimeError, match="Oops"):
        prod.unstable_schedule_callback(NORMAL_PRIORITY, bad, {"label": "Bad"})
        prod._scheduler.run_until_idle()  # type: ignore[attr-defined]  # noqa: SLF001

    fg = _fg()
    assert "errored" in fg


def test_production_profiling_overflow_records_warning() -> None:
    # Use a tiny buffer to deterministically overflow.
    prev_buffer = prod._profiling_buffer  # noqa: SLF001
    prev_prof = prod.unstable_Profiling
    try:
        prod._profiling_buffer = SchedulerProfilingBuffer(max_capacity=64)  # type: ignore[assignment]  # noqa: SLF001
        prod.unstable_Profiling = ProfilingEventLogger(  # type: ignore[assignment]
            prod._profiling_buffer,  # noqa: SLF001
            emit_overflow_warning=prod._emit_profiling_overflow,  # noqa: SLF001
        )
        prod._profiling_warnings.clear()  # noqa: SLF001
        prod.unstable_Profiling.start_logging_profiling_events()

        # Fill with many schedule/run cycles until overflow clears the buffer.
        for _ in range(200):
            prod.unstable_schedule_callback(NORMAL_PRIORITY, lambda _d: None)
        prod._scheduler.run_until_idle()  # type: ignore[attr-defined]  # noqa: SLF001

        assert prod._profiling_warnings == [PROFILING_OVERFLOW_MESSAGE]  # noqa: SLF001
        assert _fg() in ("(empty profile)", "\n!!! Main thread              │\n")
    finally:
        prod._profiling_buffer = prev_buffer  # type: ignore[assignment]  # noqa: SLF001
        prod.unstable_Profiling = prev_prof  # type: ignore[assignment]

