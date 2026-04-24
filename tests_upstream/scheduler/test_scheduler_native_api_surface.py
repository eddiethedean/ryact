from __future__ import annotations

from collections.abc import Iterator

import pytest
from schedulyr import native_scheduler
from schedulyr import production_scheduler as fallback


@pytest.fixture(autouse=True)
def _clear_native_runtime() -> Iterator[None]:
    native_scheduler.clear_native_runtime_scheduler()
    # Avoid leaking state into other production-scheduler tests: `production_scheduler`
    # maintains a module-level scheduler with incrementing task ids.
    fallback._scheduler = fallback.Scheduler()  # type: ignore[attr-defined]  # noqa: SLF001
    fallback._cancelled.clear()  # type: ignore[attr-defined]  # noqa: SLF001
    fallback._current_priority_level = fallback.NORMAL_PRIORITY  # type: ignore[attr-defined]  # noqa: SLF001
    fallback._needs_paint = False  # type: ignore[attr-defined]  # noqa: SLF001
    yield
    native_scheduler.clear_native_runtime_scheduler()
    fallback._scheduler = fallback.Scheduler()  # type: ignore[attr-defined]  # noqa: SLF001
    fallback._cancelled.clear()  # type: ignore[attr-defined]  # noqa: SLF001
    fallback._current_priority_level = fallback.NORMAL_PRIORITY  # type: ignore[attr-defined]  # noqa: SLF001
    fallback._needs_paint = False  # type: ignore[attr-defined]  # noqa: SLF001


def test_disabled_apis_throw_and_profiling_is_none() -> None:
    assert native_scheduler.unstable_Profiling is None

    with pytest.raises(RuntimeError, match=r"^Not implemented\.$"):
        native_scheduler.unstable_next()
    with pytest.raises(RuntimeError, match=r"^Not implemented\.$"):
        native_scheduler.unstable_run_with_priority()
    with pytest.raises(RuntimeError, match=r"^Not implemented\.$"):
        native_scheduler.unstable_wrap_callback()
    with pytest.raises(RuntimeError, match=r"^Not implemented\.$"):
        native_scheduler.unstable_force_frame_rate()


def test_falls_back_to_production_scheduler_when_no_native_runtime_is_injected() -> None:
    assert native_scheduler.unstable_get_current_priority_level() == fallback.NORMAL_PRIORITY
    assert isinstance(native_scheduler.unstable_now(), float)

    ran: list[str] = []

    def cb(_did_timeout: bool) -> None:
        ran.append("ok")

    task = native_scheduler.unstable_schedule_callback(fallback.NORMAL_PRIORITY, cb)
    native_scheduler.unstable_cancel_callback(task)


def test_delegates_to_injected_native_runtime() -> None:
    calls: list[tuple[str, object]] = []

    class FakeNativeRuntime:
        unstable_ImmediatePriority = 11
        unstable_UserBlockingPriority = 12
        unstable_NormalPriority = 13
        unstable_LowPriority = 14
        unstable_IdlePriority = 15

        def unstable_schedule_callback(self, priority_level: int, callback: object) -> object:
            calls.append(("schedule", priority_level))
            return ("task", priority_level, callback)

        def unstable_cancel_callback(self, task: object) -> None:
            calls.append(("cancel", task))

        def unstable_get_current_priority_level(self) -> int:
            calls.append(("get_current_priority", None))
            return 99

        def unstable_should_yield(self) -> bool:
            calls.append(("should_yield", None))
            return True

        def unstable_request_paint(self) -> None:
            calls.append(("request_paint", None))

        def unstable_now(self) -> float:
            calls.append(("now", None))
            return 123.0

    rt = FakeNativeRuntime()
    native_scheduler.set_native_runtime_scheduler(rt)

    # Priorities are dynamically resolved (post-injection).
    assert native_scheduler.unstable_ImmediatePriority == 11
    assert native_scheduler.unstable_UserBlockingPriority == 12
    assert native_scheduler.unstable_NormalPriority == 13
    assert native_scheduler.unstable_LowPriority == 14
    assert native_scheduler.unstable_IdlePriority == 15

    assert native_scheduler.unstable_get_current_priority_level() == 99
    assert native_scheduler.unstable_should_yield() is True
    native_scheduler.unstable_request_paint()
    assert native_scheduler.unstable_now() == 123.0

    t = native_scheduler.unstable_schedule_callback(7, object())
    native_scheduler.unstable_cancel_callback(t)

    assert [c[0] for c in calls] == [
        "get_current_priority",
        "should_yield",
        "request_paint",
        "now",
        "schedule",
        "cancel",
    ]
