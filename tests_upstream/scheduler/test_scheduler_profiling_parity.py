"""
Parity with ``SchedulerProfiling-test.js`` when ``enableProfiling`` is on
(``scheduler/unstable_mock`` + profiling buffer).
"""

from __future__ import annotations

import pytest
from schedulyr import unstable_NormalPriority, unstable_UserBlockingPriority
from schedulyr.mock_scheduler import UnstableMockScheduler
from schedulyr.scheduler_profiling_buffer import PROFILING_OVERFLOW_MESSAGE

from tests_upstream.scheduler.mock_scheduler_test_utils import (
    wait_for,
    wait_for_all,
    wait_for_throw,
)
from tests_upstream.scheduler.profiling_flamegraph import (
    stop_profiling_and_print_flamegraph,
)


@pytest.fixture()
def s() -> UnstableMockScheduler:
    sch = UnstableMockScheduler(enable_profiling=True)
    assert sch.unstable_profiling is not None
    sch.unstable_profiling.start_logging_profiling_events()
    return sch


def _fg(sch: UnstableMockScheduler) -> str:
    prof = sch.unstable_profiling
    assert prof is not None
    raw = prof.stop_logging_profiling_events()
    return stop_profiling_and_print_flamegraph(raw)


def _pad_label(base: str, width: int = 30) -> str:
    """Match ``SchedulerProfiling-test.js`` ``labelColumnWidth - length - 1`` padding."""
    return base + " " * (width - len(base) - 1)


def test_creates_a_basic_flamegraph(s: UnstableMockScheduler) -> None:
    sch = s
    sch.unstable_advance_time(100)

    def outer(_d: bool):
        sch.unstable_advance_time(300)
        sch.log("Yield 1")

        def inner(_d2: bool):
            sch.log("Yield 2")
            sch.unstable_advance_time(300)
            return None

        sch.unstable_schedule_callback(
            unstable_UserBlockingPriority,
            inner,
            {"label": "Bar"},
        )
        sch.unstable_advance_time(100)
        sch.log("Yield 3")

        def cont(_d3: bool):
            sch.log("Yield 4")
            sch.unstable_advance_time(300)
            return None

        return cont

    sch.unstable_schedule_callback(
        unstable_NormalPriority,
        outer,
        {"label": "Foo"},
    )
    wait_for(sch, ["Yield 1", "Yield 3"])
    sch.unstable_advance_time(100)
    wait_for_all(sch, ["Yield 2", "Yield 4"])
    expected = (
        "\n!!! Main thread              │██░░░░░░░░██░░░░░░░░░░░░\n"
        "Task 2 [User-blocking]       │        ░░░░██████\n"
        "Task 1 [Normal]              │  ████████░░░░░░░░██████\n"
    )
    assert _fg(sch) == expected


def test_marks_when_a_task_is_canceled(s: UnstableMockScheduler) -> None:
    sch = s

    def task(_d: bool):
        sch.log("Yield 1")
        sch.unstable_advance_time(300)
        sch.log("Yield 2")

        def cont(_d2: bool):
            sch.log("Continuation")
            sch.unstable_advance_time(200)
            return None

        return cont

    t = sch.unstable_schedule_callback(unstable_NormalPriority, task)
    wait_for(sch, ["Yield 1", "Yield 2"])
    sch.unstable_advance_time(100)
    sch.unstable_cancel_callback(t)
    sch.unstable_advance_time(1000)
    wait_for_all(sch, [])
    expected = (
        "\n!!! Main thread              │░░░░░░██████████████████████\n"
        "Task 1 [Normal]              │██████░░🡐 canceled\n"
    )
    assert _fg(sch) == expected


def test_marks_when_a_task_errors(s: UnstableMockScheduler) -> None:
    sch = s

    def bad(_d: bool):
        sch.unstable_advance_time(300)
        raise RuntimeError("Oops")

    sch.unstable_schedule_callback(unstable_NormalPriority, bad)
    wait_for_throw(sch, "Oops")
    sch.unstable_advance_time(100)
    sch.unstable_advance_time(1000)
    wait_for_all(sch, [])
    expected = (
        "\n!!! Main thread              │░░░░░░██████████████████████\n"
        "Task 1 [Normal]              │██████🡐 errored\n"
    )
    assert _fg(sch) == expected


def test_marks_when_multiple_tasks_are_canceled(s: UnstableMockScheduler) -> None:
    sch = s

    def task1(_d: bool):
        sch.log("Yield 1")
        sch.unstable_advance_time(300)
        sch.log("Yield 2")

        def c1(_d2: bool):
            sch.log("Continuation")
            sch.unstable_advance_time(200)
            return None

        return c1

    def task2(_d: bool):
        sch.log("Yield 3")
        sch.unstable_advance_time(300)
        sch.log("Yield 4")

        def c2(_d2: bool):
            sch.log("Continuation")
            sch.unstable_advance_time(200)
            return None

        return c2

    t1 = sch.unstable_schedule_callback(unstable_NormalPriority, task1)
    t2 = sch.unstable_schedule_callback(unstable_NormalPriority, task2)
    wait_for(sch, ["Yield 1", "Yield 2"])
    sch.unstable_advance_time(100)
    sch.unstable_cancel_callback(t1)
    sch.unstable_cancel_callback(t2)
    sch.unstable_advance_time(1000)
    wait_for_all(sch, [])
    expected = (
        "\n!!! Main thread              │░░░░░░██████████████████████\n"
        "Task 1 [Normal]              │██████░░🡐 canceled\n"
        "Task 2 [Normal]              │░░░░░░░░🡐 canceled\n"
    )
    assert _fg(sch) == expected


def test_handles_cancelling_a_task_that_already_finished(s: UnstableMockScheduler) -> None:
    sch = s

    def task(_d: bool):
        sch.log("A")
        sch.unstable_advance_time(1000)
        return None

    t = sch.unstable_schedule_callback(unstable_NormalPriority, task)
    wait_for_all(sch, ["A"])
    sch.unstable_cancel_callback(t)
    expected = (
        "\n!!! Main thread              │░░░░░░░░░░░░░░░░░░░░\n"
        "Task 1 [Normal]              │████████████████████\n"
    )
    assert _fg(sch) == expected


def test_handles_cancelling_a_task_multiple_times(s: UnstableMockScheduler) -> None:
    sch = s

    def a(_d: bool):
        sch.log("A")
        sch.unstable_advance_time(1000)
        return None

    sch.unstable_schedule_callback(unstable_NormalPriority, a, {"label": "A"})
    sch.unstable_advance_time(200)

    def b(_d: bool):
        sch.log("B")
        sch.unstable_advance_time(1000)
        return None

    t = sch.unstable_schedule_callback(unstable_NormalPriority, b, {"label": "B"})
    sch.unstable_advance_time(400)
    sch.unstable_cancel_callback(t)
    sch.unstable_cancel_callback(t)
    sch.unstable_cancel_callback(t)
    wait_for_all(sch, ["A"])
    expected = (
        "\n!!! Main thread              │████████████░░░░░░░░░░░░░░░░░░░░\n"
        "Task 1 [Normal]              │░░░░░░░░░░░░████████████████████\n"
        "Task 2 [Normal]              │    ░░░░░░░░🡐 canceled\n"
    )
    assert _fg(sch) == expected


def test_handles_delayed_tasks(s: UnstableMockScheduler) -> None:
    sch = s

    def task(_d: bool):
        sch.unstable_advance_time(1000)
        sch.log("A")
        return None

    sch.unstable_schedule_callback(
        unstable_NormalPriority,
        task,
        {"delay": 1000},
    )
    wait_for_all(sch, [])
    sch.unstable_advance_time(1000)
    wait_for_all(sch, ["A"])
    expected = (
        "\n!!! Main thread              │████████████████████░░░░░░░░░░░░░░░░░░░░\n"
        "Task 1 [Normal]              │                    ████████████████████\n"
    )
    assert _fg(sch) == expected


def test_handles_cancelling_a_delayed_task(s: UnstableMockScheduler) -> None:
    sch = s
    t = sch.unstable_schedule_callback(
        unstable_NormalPriority,
        lambda _d: sch.log("A"),
        {"delay": 1000},
    )
    sch.unstable_cancel_callback(t)
    wait_for_all(sch, [])
    expected = "\n!!! Main thread              │\n"
    assert _fg(sch) == expected


def test_automatically_stops_profiling_and_warns_if_event_log_gets_too_big() -> None:
    sch = UnstableMockScheduler(enable_profiling=True, profiling_max_event_log_size=64)
    assert sch.unstable_profiling is not None
    sch.unstable_profiling.start_logging_profiling_events()
    task_id = 1
    while not sch._profiling_warnings:  # noqa: SLF001
        task_id += 1
        t = sch.unstable_schedule_callback(unstable_NormalPriority, lambda _d: None)
        sch.unstable_cancel_callback(t)
        sch.unstable_flush_all()
    assert len(sch._profiling_warnings) == 1  # noqa: SLF001
    assert sch._profiling_warnings[0] == PROFILING_OVERFLOW_MESSAGE  # noqa: SLF001
    assert (
        stop_profiling_and_print_flamegraph(sch.unstable_profiling.stop_logging_profiling_events())
        == "(empty profile)"
    )

    sch.unstable_profiling.start_logging_profiling_events()

    def _tail_task(_d: bool) -> None:
        sch.unstable_advance_time(1000)

    sch.unstable_schedule_callback(unstable_NormalPriority, _tail_task)
    wait_for_all(sch, [])
    tail = (
        "\n!!! Main thread              │░░░░░░░░░░░░░░░░░░░░\n"
        f"{_pad_label(f'Task {task_id} [Normal]')}│████████████████████\n"
    )
    assert (
        stop_profiling_and_print_flamegraph(sch.unstable_profiling.stop_logging_profiling_events())
        == tail
    )
