"""React ``SchedulerFeatureFlags`` / Jest ``gate`` subset shared by browser-style harnesses."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass


@dataclass
class SchedulerBrowserFlags:
    """Subset of ``SchedulerFeatureFlags.js`` + Jest ``gate`` bundles."""

    enable_profiling: bool = False
    frame_yield_ms: float = 5.0
    user_blocking_priority_timeout: float = 250.0
    normal_priority_timeout: float = 5000.0
    low_priority_timeout: float = 10000.0
    enable_request_paint: bool = True
    enable_always_yield_scheduler: bool = False
    www: bool = False

    def gate(self, fn: Callable[[SchedulerBrowserFlags], bool]) -> bool:
        return bool(fn(self))
