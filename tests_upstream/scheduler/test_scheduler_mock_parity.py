"""
Parity with ``Scheduler`` + ``scheduler/unstable_mock`` in
``packages/scheduler/src/__tests__/SchedulerMock-test.js``.
"""

from __future__ import annotations

from typing import Any

import pytest
from schedulyr import (
    unstable_ImmediatePriority,
    unstable_NormalPriority,
    unstable_UserBlockingPriority,
)
from schedulyr.mock_scheduler import UnstableMockScheduler

from tests_upstream.scheduler.mock_scheduler_test_utils import (
    assert_log,
    wait_for,
    wait_for_all,
    wait_for_paint,
)


def _js_bool(b: bool) -> str:
    return "true" if b else "false"


@pytest.fixture()
def s() -> UnstableMockScheduler:
    return UnstableMockScheduler()


def test_flushes_work_incrementally(s: UnstableMockScheduler) -> None:
    sch = s
    sch.unstable_schedule_callback(unstable_NormalPriority, lambda _d: sch.log("A"))
    sch.unstable_schedule_callback(unstable_NormalPriority, lambda _d: sch.log("B"))
    sch.unstable_schedule_callback(unstable_NormalPriority, lambda _d: sch.log("C"))
    sch.unstable_schedule_callback(unstable_NormalPriority, lambda _d: sch.log("D"))
    wait_for(sch, ["A", "B"])
    wait_for(sch, ["C"])
    wait_for_all(sch, ["D"])


def test_cancels_work(s: UnstableMockScheduler) -> None:
    sch = s
    sch.unstable_schedule_callback(unstable_NormalPriority, lambda _d: sch.log("A"))
    h_b = sch.unstable_schedule_callback(unstable_NormalPriority, lambda _d: sch.log("B"))
    sch.unstable_schedule_callback(unstable_NormalPriority, lambda _d: sch.log("C"))
    sch.unstable_cancel_callback(h_b)
    wait_for_all(sch, ["A", "C"])


def test_executes_the_highest_priority_callbacks_first(s: UnstableMockScheduler) -> None:
    sch = s
    sch.unstable_schedule_callback(unstable_NormalPriority, lambda _d: sch.log("A"))
    sch.unstable_schedule_callback(unstable_NormalPriority, lambda _d: sch.log("B"))
    wait_for(sch, ["A"])
    sch.unstable_schedule_callback(unstable_UserBlockingPriority, lambda _d: sch.log("C"))
    sch.unstable_schedule_callback(unstable_UserBlockingPriority, lambda _d: sch.log("D"))
    wait_for_all(sch, ["C", "D", "B"])


def test_expires_work(s: UnstableMockScheduler) -> None:
    sch = s
    sch.unstable_schedule_callback(
        unstable_NormalPriority,
        lambda did: sch.unstable_advance_time(100) or sch.log(f"A (did timeout: {_js_bool(did)})"),
    )
    sch.unstable_schedule_callback(
        unstable_UserBlockingPriority,
        lambda did: sch.unstable_advance_time(100) or sch.log(f"B (did timeout: {_js_bool(did)})"),
    )
    sch.unstable_schedule_callback(
        unstable_UserBlockingPriority,
        lambda did: sch.unstable_advance_time(100) or sch.log(f"C (did timeout: {_js_bool(did)})"),
    )
    sch.unstable_advance_time(249)
    assert_log(sch, [])
    sch.unstable_schedule_callback(
        unstable_NormalPriority,
        lambda did: sch.unstable_advance_time(100) or sch.log(f"D (did timeout: {_js_bool(did)})"),
    )
    sch.unstable_schedule_callback(
        unstable_NormalPriority,
        lambda did: sch.unstable_advance_time(100) or sch.log(f"E (did timeout: {_js_bool(did)})"),
    )
    sch.unstable_advance_time(1)
    wait_for(sch, ["B (did timeout: true)", "C (did timeout: true)"])
    sch.unstable_advance_time(4600)
    wait_for(sch, ["A (did timeout: true)"])
    wait_for_all(sch, ["D (did timeout: false)", "E (did timeout: true)"])


def test_has_a_default_expiration_of_5_seconds(s: UnstableMockScheduler) -> None:
    sch = s
    sch.unstable_schedule_callback(unstable_NormalPriority, lambda _d: sch.log("A"))
    sch.unstable_advance_time(4999)
    assert_log(sch, [])
    sch.unstable_advance_time(1)
    sch.unstable_flush_expired()
    assert_log(sch, ["A"])


def test_continues_working_on_same_task_after_yielding(s: UnstableMockScheduler) -> None:
    sch = s
    sch.unstable_schedule_callback(
        unstable_NormalPriority,
        lambda _d: sch.unstable_advance_time(100) or sch.log("A"),
    )
    sch.unstable_schedule_callback(
        unstable_NormalPriority,
        lambda _d: sch.unstable_advance_time(100) or sch.log("B"),
    )
    tasks = [["C1", 100.0], ["C2", 100.0], ["C3", 100.0]]
    did_yield = False

    def c(_did: bool):
        nonlocal did_yield
        while tasks:
            label, ms = tasks.pop(0)
            sch.unstable_advance_time(ms)
            sch.log(label)
            if sch.unstable_should_yield():
                did_yield = True
                return c
        return None

    sch.unstable_schedule_callback(unstable_NormalPriority, c)
    sch.unstable_schedule_callback(
        unstable_NormalPriority,
        lambda _d: sch.unstable_advance_time(100) or sch.log("D"),
    )
    sch.unstable_schedule_callback(
        unstable_NormalPriority,
        lambda _d: sch.unstable_advance_time(100) or sch.log("E"),
    )
    assert not did_yield
    wait_for(sch, ["A", "B", "C1"])
    assert did_yield
    wait_for_all(sch, ["C2", "C3", "D", "E"])


def test_continuation_callbacks_inherit_the_expiration_of_the_previous_callback(
    s: UnstableMockScheduler,
) -> None:
    sch = s
    tasks = [["A", 125.0], ["B", 124.0], ["C", 100.0], ["D", 100.0]]

    def work(_did: bool):
        while tasks:
            label, ms = tasks.pop(0)
            sch.unstable_advance_time(ms)
            sch.log(label)
            if sch.unstable_should_yield():
                return work
        return None

    sch.unstable_schedule_callback(unstable_UserBlockingPriority, work)
    wait_for(sch, ["A", "B"])
    sch.unstable_advance_time(1)
    sch.unstable_flush_expired()
    assert_log(sch, ["C", "D"])


def test_continuations_are_interrupted_by_higher_priority_work(s: UnstableMockScheduler) -> None:
    sch = s
    tasks = [["A", 100.0], ["B", 100.0], ["C", 100.0], ["D", 100.0]]

    def work(_did: bool):
        while tasks:
            label, ms = tasks.pop(0)
            sch.unstable_advance_time(ms)
            sch.log(label)
            if tasks and sch.unstable_should_yield():
                return work
        return None

    sch.unstable_schedule_callback(unstable_NormalPriority, work)
    wait_for(sch, ["A"])
    sch.unstable_schedule_callback(
        unstable_UserBlockingPriority,
        lambda _d: sch.unstable_advance_time(100) or sch.log("High pri"),
    )
    wait_for_all(sch, ["High pri", "B", "C", "D"])


def test_continuations_do_not_block_higher_priority_work_scheduled_inside_an_executing_callback(
    s: UnstableMockScheduler,
) -> None:
    sch = s
    tasks = [["A", 100.0], ["B", 100.0], ["C", 100.0], ["D", 100.0]]

    def work(_did: bool):
        while tasks:
            label, ms = tasks.pop(0)
            sch.unstable_advance_time(ms)
            sch.log(label)
            if label == "B":
                sch.log("Schedule high pri")
                sch.unstable_schedule_callback(
                    unstable_UserBlockingPriority,
                    lambda _d: sch.unstable_advance_time(100) or sch.log("High pri"),
                )
            if tasks:
                return work
        return None

    sch.unstable_schedule_callback(unstable_NormalPriority, work)
    wait_for_all(
        sch,
        ["A", "B", "Schedule high pri", "High pri", "C", "D"],
    )


def test_cancelling_a_continuation(s: UnstableMockScheduler) -> None:
    sch = s
    h = sch.unstable_schedule_callback(
        unstable_NormalPriority,
        lambda _d: sch.log("Yield") or (lambda _d2: sch.log("Continuation")),
    )
    wait_for(sch, ["Yield"])
    sch.unstable_cancel_callback(h)
    wait_for_all(sch, [])


def test_top_level_immediate_callbacks_fire_in_a_subsequent_task(s: UnstableMockScheduler) -> None:
    sch = s
    sch.unstable_schedule_callback(unstable_ImmediatePriority, lambda _d: sch.log("A"))
    sch.unstable_schedule_callback(unstable_ImmediatePriority, lambda _d: sch.log("B"))
    sch.unstable_schedule_callback(unstable_ImmediatePriority, lambda _d: sch.log("C"))
    sch.unstable_schedule_callback(unstable_ImmediatePriority, lambda _d: sch.log("D"))
    assert_log(sch, [])
    sch.unstable_flush_expired()
    assert_log(sch, ["A", "B", "C", "D"])


def test_nested_immediate_callbacks_are_added_to_the_queue_of_immediate_callbacks(
    s: UnstableMockScheduler,
) -> None:
    sch = s
    sch.unstable_schedule_callback(unstable_ImmediatePriority, lambda _d: sch.log("A"))
    sch.unstable_schedule_callback(
        unstable_ImmediatePriority,
        lambda _d: sch.log("B")
        or sch.unstable_schedule_callback(unstable_ImmediatePriority, lambda _d2: sch.log("C")),
    )
    sch.unstable_schedule_callback(unstable_ImmediatePriority, lambda _d: sch.log("D"))
    assert_log(sch, [])
    sch.unstable_flush_expired()
    assert_log(sch, ["A", "B", "D", "C"])


def test_wrapped_callbacks_have_same_signature_as_original_callback(
    s: UnstableMockScheduler,
) -> None:
    sch = s
    wrapped = sch.unstable_wrap_callback(lambda *args: {"args": list(args)})
    assert wrapped("a", "b") == {"args": ["a", "b"]}


def test_wrapped_callbacks_inherit_the_current_priority(s: UnstableMockScheduler) -> None:
    sch = s

    def log_pri() -> None:
        sch.log(sch.unstable_get_current_priority_level())

    def wrap_normal() -> Any:
        return sch.unstable_wrap_callback(log_pri)

    def wrap_ub() -> Any:
        return sch.unstable_wrap_callback(log_pri)

    wrapped = sch.unstable_run_with_priority(unstable_NormalPriority, wrap_normal)
    wrapped_ub = sch.unstable_run_with_priority(unstable_UserBlockingPriority, wrap_ub)
    wrapped()
    assert_log(sch, [unstable_NormalPriority])
    wrapped_ub()
    assert_log(sch, [unstable_UserBlockingPriority])


def test_wrapped_callbacks_inherit_the_current_priority_even_when_nested(
    s: UnstableMockScheduler,
) -> None:
    sch = s

    def log_pri() -> None:
        sch.log(sch.unstable_get_current_priority_level())

    def wrap_n() -> Any:
        return sch.unstable_wrap_callback(log_pri)

    def wrap_nested() -> Any:
        return sch.unstable_run_with_priority(
            unstable_UserBlockingPriority,
            lambda: sch.unstable_wrap_callback(log_pri),
        )

    wrapped = sch.unstable_run_with_priority(unstable_NormalPriority, wrap_n)
    wrapped_ub = sch.unstable_run_with_priority(unstable_NormalPriority, wrap_nested)
    wrapped()
    assert_log(sch, [unstable_NormalPriority])
    wrapped_ub()
    assert_log(sch, [unstable_UserBlockingPriority])


def test_immediate_callbacks_fire_even_if_there_s_an_error(s: UnstableMockScheduler) -> None:
    sch = s

    def a(_d: bool):
        sch.log("A")
        raise RuntimeError("Oops A")

    def c(_d: bool):
        sch.log("C")
        raise RuntimeError("Oops C")

    sch.unstable_schedule_callback(unstable_ImmediatePriority, a)
    sch.unstable_schedule_callback(unstable_ImmediatePriority, lambda _d: sch.log("B"))
    sch.unstable_schedule_callback(unstable_ImmediatePriority, c)
    with pytest.raises(RuntimeError, match="Oops A"):
        sch.unstable_flush_expired()
    assert_log(sch, ["A"])
    with pytest.raises(RuntimeError, match="Oops C"):
        sch.unstable_flush_expired()
    assert_log(sch, ["B", "C"])


def test_multiple_immediate_callbacks_can_throw_and_there_will_be_an_error_for_each_one(
    s: UnstableMockScheduler,
) -> None:
    sch = s

    def raise_first(_d: bool) -> None:
        raise RuntimeError("First error")

    def raise_second(_d: bool) -> None:
        raise RuntimeError("Second error")

    sch.unstable_schedule_callback(unstable_ImmediatePriority, raise_first)
    sch.unstable_schedule_callback(unstable_ImmediatePriority, raise_second)
    with pytest.raises(RuntimeError, match="First error"):
        sch.unstable_flush_all()
    with pytest.raises(RuntimeError, match="Second error"):
        sch.unstable_flush_all()


def test_exposes_the_current_priority_level(s: UnstableMockScheduler) -> None:
    sch = s
    sch.log(sch.unstable_get_current_priority_level())

    def in_immediate() -> None:
        sch.log(sch.unstable_get_current_priority_level())

        def in_normal() -> None:
            sch.log(sch.unstable_get_current_priority_level())
            sch.unstable_run_with_priority(
                unstable_UserBlockingPriority,
                lambda: sch.log(sch.unstable_get_current_priority_level()),
            )

        sch.unstable_run_with_priority(unstable_NormalPriority, in_normal)
        sch.log(sch.unstable_get_current_priority_level())

    sch.unstable_run_with_priority(unstable_ImmediatePriority, in_immediate)
    assert_log(
        sch,
        [
            unstable_NormalPriority,
            unstable_ImmediatePriority,
            unstable_NormalPriority,
            unstable_UserBlockingPriority,
            unstable_ImmediatePriority,
        ],
    )


def test_delayed_tasks_schedules_a_delayed_task(s: UnstableMockScheduler) -> None:
    sch = s
    sch.unstable_schedule_callback(
        unstable_NormalPriority,
        lambda _d: sch.log("A"),
        {"delay": 1000},
    )
    wait_for_all(sch, [])
    sch.unstable_advance_time(999)
    wait_for_all(sch, [])
    sch.unstable_advance_time(1)
    wait_for_all(sch, ["A"])


def test_delayed_tasks_schedules_multiple_delayed_tasks(s: UnstableMockScheduler) -> None:
    sch = s
    sch.unstable_schedule_callback(unstable_NormalPriority, lambda _d: sch.log("C"), {"delay": 300})
    sch.unstable_schedule_callback(unstable_NormalPriority, lambda _d: sch.log("B"), {"delay": 200})
    sch.unstable_schedule_callback(unstable_NormalPriority, lambda _d: sch.log("D"), {"delay": 400})
    sch.unstable_schedule_callback(unstable_NormalPriority, lambda _d: sch.log("A"), {"delay": 100})
    wait_for_all(sch, [])
    sch.unstable_advance_time(200)
    wait_for(sch, ["A"])
    wait_for_all(sch, ["B"])
    sch.unstable_advance_time(200)
    wait_for_all(sch, ["C", "D"])


def test_delayed_tasks_interleaves_normal_tasks_and_delayed_tasks(s: UnstableMockScheduler) -> None:
    sch = s
    sch.unstable_schedule_callback(
        unstable_UserBlockingPriority, lambda _d: sch.log("Timer 2"), {"delay": 300}
    )
    sch.unstable_schedule_callback(
        unstable_UserBlockingPriority, lambda _d: sch.log("Timer 1"), {"delay": 100}
    )
    sch.unstable_schedule_callback(
        unstable_NormalPriority,
        lambda _d: sch.log("A") or sch.unstable_advance_time(100),
    )
    sch.unstable_schedule_callback(
        unstable_NormalPriority,
        lambda _d: sch.log("B") or sch.unstable_advance_time(100),
    )
    sch.unstable_schedule_callback(
        unstable_NormalPriority,
        lambda _d: sch.log("C") or sch.unstable_advance_time(100),
    )
    sch.unstable_schedule_callback(
        unstable_NormalPriority,
        lambda _d: sch.log("D") or sch.unstable_advance_time(100),
    )
    wait_for_all(sch, ["A", "Timer 1", "B", "C", "Timer 2", "D"])


def test_delayed_tasks_interleaves_delayed_tasks_with_time_sliced_tasks(
    s: UnstableMockScheduler,
) -> None:
    sch = s
    sch.unstable_schedule_callback(
        unstable_UserBlockingPriority, lambda _d: sch.log("Timer 2"), {"delay": 300}
    )
    sch.unstable_schedule_callback(
        unstable_UserBlockingPriority, lambda _d: sch.log("Timer 1"), {"delay": 100}
    )
    tasks = [["A", 100.0], ["B", 100.0], ["C", 100.0], ["D", 100.0]]

    def work(_did: bool):
        while tasks:
            t = tasks.pop(0)
            label, ms = t
            sch.unstable_advance_time(ms)
            sch.log(label)
            if tasks:
                return work
        return None

    sch.unstable_schedule_callback(unstable_NormalPriority, work)
    wait_for_all(sch, ["A", "Timer 1", "B", "C", "Timer 2", "D"])


def test_delayed_tasks_cancels_a_delayed_task(s: UnstableMockScheduler) -> None:
    sch = s
    opts = {"delay": 100}
    sch.unstable_schedule_callback(unstable_NormalPriority, lambda _d: sch.log("A"), opts)
    h_b = sch.unstable_schedule_callback(unstable_NormalPriority, lambda _d: sch.log("B"), opts)
    h_c = sch.unstable_schedule_callback(unstable_NormalPriority, lambda _d: sch.log("C"), opts)
    wait_for_all(sch, [])
    sch.unstable_cancel_callback(h_b)
    sch.unstable_advance_time(500)
    sch.unstable_cancel_callback(h_c)
    wait_for_all(sch, ["A"])


def test_delayed_tasks_gracefully_handles_scheduled_tasks_that_are_not_a_function(
    s: UnstableMockScheduler,
) -> None:
    sch = s
    sch.unstable_schedule_callback(unstable_ImmediatePriority, None)  # type: ignore[arg-type]
    wait_for_all(sch, [])
    sch.unstable_schedule_callback(unstable_ImmediatePriority, None)  # type: ignore[arg-type]
    wait_for_all(sch, [])
    sch.unstable_schedule_callback(unstable_ImmediatePriority, {})  # type: ignore[arg-type]
    wait_for_all(sch, [])
    sch.unstable_schedule_callback(unstable_ImmediatePriority, 42)  # type: ignore[arg-type]
    wait_for_all(sch, [])


def test_delayed_tasks_toflushuntilnextpaint_stops_if_a_continuation_is_returned(
    s: UnstableMockScheduler,
) -> None:
    sch = s
    shy = sch.unstable_should_yield

    def task(_d: bool):
        sch.log("Original Task")
        sch.log(f"shouldYield: {_js_bool(shy())}")
        sch.log("Return a continuation")
        return lambda _d2: sch.log("Continuation Task")

    sch.unstable_schedule_callback(unstable_NormalPriority, task)
    wait_for_paint(
        sch,
        ["Original Task", "shouldYield: false", "Return a continuation"],
    )
    assert sch.unstable_now() == 0
    wait_for_all(sch, ["Continuation Task"])


def test_delayed_tasks_toflushandyield_keeps_flushing_even_if_there_s_a_continuation(
    s: UnstableMockScheduler,
) -> None:
    sch = s
    shy = sch.unstable_should_yield

    def task(_d: bool):
        sch.log("Original Task")
        sch.log(f"shouldYield: {_js_bool(shy())}")
        sch.log("Return a continuation")
        return lambda _d2: sch.log("Continuation Task")

    sch.unstable_schedule_callback(unstable_NormalPriority, task)
    wait_for_all(
        sch,
        ["Original Task", "shouldYield: false", "Return a continuation", "Continuation Task"],
    )
