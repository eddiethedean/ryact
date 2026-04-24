from __future__ import annotations

from typing import Any, Optional, Protocol

from . import production_scheduler as _fallback


class NativeRuntimeScheduler(Protocol):
    """
    Python analogue of upstream `nativeRuntimeScheduler` (SchedulerNative.js).

    This reflects the subset of Scheduler APIs that the React Native runtime scheduler
    binding supports, and that upstream `SchedulerNative.js` conditionally delegates to.
    """

    unstable_ImmediatePriority: int
    unstable_UserBlockingPriority: int
    unstable_NormalPriority: int
    unstable_LowPriority: int
    unstable_IdlePriority: int

    def unstable_schedule_callback(self, priority_level: int, callback: Any) -> Any: ...
    def unstable_cancel_callback(self, task: Any) -> None: ...
    def unstable_get_current_priority_level(self) -> int: ...
    def unstable_should_yield(self) -> bool: ...
    def unstable_request_paint(self) -> None: ...
    def unstable_now(self) -> float: ...


_native_runtime_scheduler: Optional[NativeRuntimeScheduler] = None


def set_native_runtime_scheduler(runtime: NativeRuntimeScheduler) -> None:
    global _native_runtime_scheduler
    _native_runtime_scheduler = runtime


def clear_native_runtime_scheduler() -> None:
    global _native_runtime_scheduler
    _native_runtime_scheduler = None


def _native() -> Optional[NativeRuntimeScheduler]:
    return _native_runtime_scheduler


def __getattr__(name: str) -> Any:
    """
    Resolve priority constants dynamically to match upstream delegation behavior.

    In upstream `SchedulerNative.js`, priority exports are constants whose values depend
    on whether `nativeRuntimeScheduler` exists. In Python, we allow injection to happen
    after import, so these are served via `__getattr__`.
    """

    n = _native()
    if name == "unstable_ImmediatePriority":
        return n.unstable_ImmediatePriority if n is not None else _fallback.IMMEDIATE_PRIORITY
    if name == "unstable_UserBlockingPriority":
        return (
            n.unstable_UserBlockingPriority if n is not None else _fallback.USER_BLOCKING_PRIORITY
        )
    if name == "unstable_NormalPriority":
        return n.unstable_NormalPriority if n is not None else _fallback.NORMAL_PRIORITY
    if name == "unstable_LowPriority":
        return n.unstable_LowPriority if n is not None else _fallback.LOW_PRIORITY
    if name == "unstable_IdlePriority":
        return n.unstable_IdlePriority if n is not None else _fallback.IDLE_PRIORITY
    raise AttributeError(name)


def unstable_schedule_callback(priority_level: int, callback: Any) -> Any:
    n = _native()
    if n is not None:
        return n.unstable_schedule_callback(priority_level, callback)
    return _fallback.unstable_schedule_callback(priority_level, callback)


def unstable_cancel_callback(task: Any) -> None:
    n = _native()
    if n is not None:
        return n.unstable_cancel_callback(task)
    return _fallback.unstable_cancel_callback(task)


def unstable_get_current_priority_level() -> int:
    n = _native()
    if n is not None:
        return n.unstable_get_current_priority_level()
    return _fallback.unstable_get_current_priority_level()


def unstable_should_yield() -> bool:
    n = _native()
    if n is not None:
        return n.unstable_should_yield()
    return _fallback.unstable_should_yield()


def unstable_request_paint() -> None:
    n = _native()
    if n is not None:
        return n.unstable_request_paint()
    return _fallback.unstable_request_paint()


def unstable_now() -> float:
    n = _native()
    if n is not None:
        return float(n.unstable_now())
    return float(_fallback.unstable_now())


def _throw_not_implemented() -> None:
    raise RuntimeError("Not implemented.")


# These were never implemented on the native scheduler because React never calls them.
# For consistency, disable them altogether and make them throw (upstream shape).
unstable_next: Any = _throw_not_implemented
unstable_run_with_priority: Any = _throw_not_implemented
unstable_wrap_callback: Any = _throw_not_implemented
unstable_force_frame_rate: Any = _throw_not_implemented

# Upstream exports `null`.
unstable_Profiling: Any = None
