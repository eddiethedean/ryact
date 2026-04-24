from __future__ import annotations

from collections.abc import Callable

from schedulyr.mock_browser_runtime import MockBrowserRuntime
from schedulyr.production_dom_scheduler import ProductionDOMHarness
from schedulyr.production_host import SetTimeoutMockRuntime
from schedulyr.scheduler import NORMAL_PRIORITY
from schedulyr.scheduler_browser_flags import SchedulerBrowserFlags
from schedulyr.set_immediate_runtime import SetImmediateMockRuntime


def test_driver_selection_prefers_set_immediate_over_message_channel() -> None:
    class HybridHost(SetImmediateMockRuntime):
        def set_on_message(self, _fn: Callable[[], None] | None) -> None:
            pass

        def port2_post_message(self, _payload: object | None = None) -> None:
            self.log("Post Message")

    host = HybridHost()
    sched = ProductionDOMHarness.for_host(host)
    sched.unstable_schedule_callback(NORMAL_PRIORITY, lambda _did_timeout: None)
    host.assert_log(["Set Immediate"])


def test_driver_selection_prefers_message_channel_over_set_timeout() -> None:
    class HybridHost(MockBrowserRuntime):
        def set_timeout(self, _cb: Callable[[], None], _delay: object | None = None) -> int:  # type: ignore[override]
            self.log("Set Timer")
            return super().set_timeout(_cb, _delay)

    host = HybridHost()
    sched = ProductionDOMHarness.for_host(host)
    sched.unstable_schedule_callback(NORMAL_PRIORITY, lambda _did_timeout: None)
    host.assert_log(["Post Message"])


def test_time_slice_yield_schedules_next_host_tick() -> None:
    flags = SchedulerBrowserFlags()
    flags.frame_yield_ms = 5.0
    host = MockBrowserRuntime()
    sched = ProductionDOMHarness.for_host(host, flags=flags)

    seen: list[str] = []

    def first(_did_timeout: bool) -> None:
        seen.append("A")
        host.advance_time(6.0)

    def second(_did_timeout: bool) -> None:
        seen.append("B")

    sched.unstable_schedule_callback(NORMAL_PRIORITY, first)
    sched.unstable_schedule_callback(NORMAL_PRIORITY, second)

    host.assert_log(["Post Message"])
    host.fire_message_event()
    host.assert_log(["Message Event", "Post Message"])
    assert seen == ["A"]

    host.fire_message_event()
    host.assert_log(["Message Event"])
    assert seen == ["A", "B"]


def test_request_paint_yield_schedules_next_host_tick() -> None:
    flags = SchedulerBrowserFlags()
    flags.enable_request_paint = True
    host = MockBrowserRuntime()
    sched = ProductionDOMHarness.for_host(host, flags=flags)

    seen: list[str] = []

    def first(_did_timeout: bool) -> None:
        seen.append("A")
        sched.unstable_request_paint()

    def second(_did_timeout: bool) -> None:
        seen.append("B")

    sched.unstable_schedule_callback(NORMAL_PRIORITY, first)
    sched.unstable_schedule_callback(NORMAL_PRIORITY, second)

    host.assert_log(["Post Message"])
    host.fire_message_event()
    host.assert_log(["Message Event", "Post Message"])
    assert seen == ["A"]

    host.fire_message_event()
    host.assert_log(["Message Event"])
    assert seen == ["A", "B"]


def test_continuation_forces_host_yield() -> None:
    host = MockBrowserRuntime()
    sched = ProductionDOMHarness.for_host(host)

    seen: list[str] = []

    def first(_did_timeout: bool) -> Callable[[bool], None]:
        seen.append("A")

        def cont(_did_timeout2: bool) -> None:
            seen.append("B")

        return cont

    sched.unstable_schedule_callback(NORMAL_PRIORITY, first)

    host.assert_log(["Post Message"])
    host.fire_message_event()
    host.assert_log(["Message Event", "Post Message"])
    assert seen == ["A"]

    host.fire_message_event()
    host.assert_log(["Message Event"])
    assert seen == ["A", "B"]


def test_set_timeout_driver_runs_callbacks_in_ticks() -> None:
    host = SetTimeoutMockRuntime()
    sched = ProductionDOMHarness.for_host(host)

    seen: list[str] = []

    def first(_did_timeout: bool) -> None:
        seen.append("A")

    sched.unstable_schedule_callback(NORMAL_PRIORITY, first)
    host.assert_log(["Set Timer"])
    sched.flush_one_tick()
    host.assert_log(["SetTimeout Callback"])
    assert seen == ["A"]
