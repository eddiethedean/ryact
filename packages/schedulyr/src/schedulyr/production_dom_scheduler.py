from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Protocol, TypeAlias

from .browser_scheduler import BrowserSchedulerHarness
from .production_host import SetTimeoutMockRuntime
from .scheduler_browser_flags import SchedulerBrowserFlags
from .set_immediate_scheduler import SetImmediateSchedulerHarness
from .set_timeout_scheduler import SetTimeoutSchedulerHarness


class ProductionDOMScheduler(Protocol):
    """
    Minimal surface for production DOM host-loop parity tests.

    This is intentionally narrower than the full `production_scheduler.py` export surface.
    """

    def unstable_schedule_callback(
        self,
        priority_level: int,
        callback: Any,
        options: Any = None,
    ) -> Any: ...
    def unstable_cancel_callback(self, handle: Any) -> None: ...
    def unstable_request_paint(self) -> None: ...


Driver: TypeAlias = (
    BrowserSchedulerHarness | SetImmediateSchedulerHarness | SetTimeoutSchedulerHarness
)


@dataclass
class ProductionDOMHarness:
    """
    Default DOM fork host selection wrapper (setImmediate → MessageChannel → setTimeout(0)).

    M19 uses the existing browser-style harnesses for the timer/task heap work loop and focuses
    on driver selection + yielding/continuation behavior.
    """

    driver: Driver
    host: Any

    @staticmethod
    def for_host(
        host: Any,
        *,
        flags: Optional[SchedulerBrowserFlags] = None,
    ) -> ProductionDOMHarness:
        f = flags or SchedulerBrowserFlags()
        # setImmediate preferred
        if hasattr(host, "schedule_immediate") and hasattr(host, "set_on_immediate"):
            return ProductionDOMHarness(
                driver=SetImmediateSchedulerHarness(host, flags=f),
                host=host,
            )
        # MessageChannel next
        if hasattr(host, "port2_post_message") and hasattr(host, "set_on_message"):
            return ProductionDOMHarness(driver=BrowserSchedulerHarness(host, flags=f), host=host)
        # Fallback setTimeout(0)
        if hasattr(host, "set_timeout") and hasattr(host, "performance"):
            # `SetTimeoutSchedulerHarness` expects a `(cb, delay_ms) -> id` signature.
            drv = SetTimeoutSchedulerHarness(host.set_timeout, host.performance.now, flags=f)
            return ProductionDOMHarness(driver=drv, host=host)
        raise TypeError(f"Unsupported host object: {host!r}")

    def unstable_schedule_callback(
        self,
        priority_level: int,
        callback: Any,
        options: Any = None,
    ) -> Any:
        return self.driver.unstable_schedule_callback(priority_level, callback, options)

    def unstable_cancel_callback(self, handle: Any) -> None:
        return self.driver.unstable_cancel_callback(handle)

    def unstable_request_paint(self) -> None:
        return self.driver.unstable_request_paint()

    def flush_one_tick(self) -> None:
        """Run a single host task tick (MessageEvent / setImmediate / setTimeout callback)."""

        if hasattr(self.host, "fire_immediate"):
            self.host.fire_immediate()
            return
        if hasattr(self.host, "fire_message_event"):
            self.host.fire_message_event()
            return
        if isinstance(self.host, SetTimeoutMockRuntime):
            # Run a single pending callback (one tick).
            self.host._ensure_log_empty()  # type: ignore[attr-defined]
            if not self.host._pending:  # type: ignore[attr-defined]
                raise RuntimeError("No setTimeout was scheduled")
            cb = self.host._pending.pop(0)  # type: ignore[attr-defined]
            self.host.log("SetTimeout Callback")
            cb()
            return
        raise TypeError(f"Unsupported host type: {type(self.host)!r}")

    def has_pending_tick(self) -> bool:
        if hasattr(self.host, "_pending_immediate"):
            return self.host._pending_immediate is not None  # type: ignore[attr-defined]
        if hasattr(self.host, "_has_pending_message"):
            return bool(self.host._has_pending_message)  # type: ignore[attr-defined]
        if isinstance(self.host, SetTimeoutMockRuntime):
            return bool(self.host._pending)  # type: ignore[attr-defined]
        return False
