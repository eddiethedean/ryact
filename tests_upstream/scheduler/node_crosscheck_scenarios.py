from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from schedulyr import (
    BrowserSchedulerHarness,
    MockBrowserRuntime,
    ProductionDOMHarness,
    SchedulerBrowserFlags,
    SetImmediateMockRuntime,
    SetTimeoutMockRuntime,
    UnstableMockScheduler,
    unstable_NormalPriority,
)


@dataclass(frozen=True)
class ScenarioResult:
    name: str
    events: list[Any]


def list_scenarios() -> list[str]:
    return [
        "browser.basic_event_log",
        "mock.basic_yield_log",
        "production_dom.driver_selection.set_immediate",
        "production_dom.driver_selection.message_channel",
        "production_dom.driver_selection.set_timeout",
        "production_dom.continuation_forces_host_yield",
        "production_dom.request_paint_yields",
        "browser.should_yield.force_frame_rate",
    ]


def run_scenario(name: str) -> ScenarioResult:
    if name == "browser.basic_event_log":
        return _browser_basic_event_log()
    if name == "mock.basic_yield_log":
        return _mock_basic_yield_log()
    if name == "production_dom.driver_selection.set_immediate":
        return _production_dom_driver_selection_set_immediate()
    if name == "production_dom.driver_selection.message_channel":
        return _production_dom_driver_selection_message_channel()
    if name == "production_dom.driver_selection.set_timeout":
        return _production_dom_driver_selection_set_timeout()
    if name == "production_dom.continuation_forces_host_yield":
        return _production_dom_continuation_forces_host_yield()
    if name == "production_dom.request_paint_yields":
        return _production_dom_request_paint_yields()
    if name == "browser.should_yield.force_frame_rate":
        return _browser_should_yield_force_frame_rate()
    raise KeyError(f"Unknown scenario: {name!r}")


def _browser_basic_event_log() -> ScenarioResult:
    host = MockBrowserRuntime()
    harness = BrowserSchedulerHarness(host)

    # Log a marker from inside scheduled work, plus the host's own MessageChannel logs.
    def cb(_did_timeout: bool) -> None:
        host.log("Callback A")

    harness.unstable_schedule_callback(unstable_NormalPriority, cb)

    # Drive the message loop until no more messages are pending.
    # (This relies on the host's internal flag; this module is only for optional tooling.)
    events: list[str] = []
    while host._has_pending_message:  # type: ignore[attr-defined]
        # `fire_message_event()` requires the log to be empty, but `post_message` logs
        # "Post Message" first. Snapshot any pending log lines before firing.
        if host._event_log:  # type: ignore[attr-defined]
            events.extend(host._event_log)  # type: ignore[attr-defined]
            host._event_log = []  # type: ignore[attr-defined]
        host.fire_message_event()
        events.extend(host._event_log)  # type: ignore[attr-defined]
        host._event_log = []  # type: ignore[attr-defined]

    return ScenarioResult(name="browser.basic_event_log", events=events)


def _mock_basic_yield_log() -> ScenarioResult:
    s = UnstableMockScheduler()

    def work(_did_timeout: bool) -> None:
        s.log("A")

    s.unstable_schedule_callback(unstable_NormalPriority, work)
    s.unstable_flush_all_without_asserting()
    events = s.unstable_clear_log()

    return ScenarioResult(name="mock.basic_yield_log", events=events)


def _drain_production_dom(h: ProductionDOMHarness) -> list[str]:
    host = h.host
    events: list[str] = []
    # Similar to the browser harness draining approach: snapshot pending host logs
    # before firing ticks, because tick methods require log emptiness.
    while h.has_pending_tick():
        if hasattr(host, "_event_log") and host._event_log:  # type: ignore[attr-defined]
            events.extend(host._event_log)  # type: ignore[attr-defined]
            host._event_log = []  # type: ignore[attr-defined]
        h.flush_one_tick()
        if hasattr(host, "_event_log") and host._event_log:  # type: ignore[attr-defined]
            events.extend(host._event_log)  # type: ignore[attr-defined]
            host._event_log = []  # type: ignore[attr-defined]
    return events


def _production_dom_driver_selection_set_immediate() -> ScenarioResult:
    host = SetImmediateMockRuntime()
    h = ProductionDOMHarness.for_host(host)
    h.unstable_schedule_callback(unstable_NormalPriority, lambda _d: None)
    events = _drain_production_dom(h)
    return ScenarioResult(name="production_dom.driver_selection.set_immediate", events=events)


def _production_dom_driver_selection_message_channel() -> ScenarioResult:
    host = MockBrowserRuntime()
    h = ProductionDOMHarness.for_host(host)
    h.unstable_schedule_callback(unstable_NormalPriority, lambda _d: None)
    events = _drain_production_dom(h)
    return ScenarioResult(name="production_dom.driver_selection.message_channel", events=events)


def _production_dom_driver_selection_set_timeout() -> ScenarioResult:
    host = SetTimeoutMockRuntime()
    h = ProductionDOMHarness.for_host(host)
    h.unstable_schedule_callback(unstable_NormalPriority, lambda _d: None)
    events = _drain_production_dom(h)
    return ScenarioResult(name="production_dom.driver_selection.set_timeout", events=events)


def _production_dom_continuation_forces_host_yield() -> ScenarioResult:
    host = MockBrowserRuntime()
    h = ProductionDOMHarness.for_host(host)

    def first(_d: bool):
        host.log("Callback A")

        def cont(_d2: bool) -> None:
            host.log("Callback B")

        return cont

    h.unstable_schedule_callback(unstable_NormalPriority, first)
    events = _drain_production_dom(h)
    return ScenarioResult(name="production_dom.continuation_forces_host_yield", events=events)


def _production_dom_request_paint_yields() -> ScenarioResult:
    flags = SchedulerBrowserFlags()
    flags.enable_request_paint = True
    host = MockBrowserRuntime()
    h = ProductionDOMHarness.for_host(host, flags=flags)

    def first(_d: bool) -> None:
        host.log("Callback A")
        h.unstable_request_paint()

    def second(_d: bool) -> None:
        host.log("Callback B")

    h.unstable_schedule_callback(unstable_NormalPriority, first)
    h.unstable_schedule_callback(unstable_NormalPriority, second)

    events = _drain_production_dom(h)
    return ScenarioResult(name="production_dom.request_paint_yields", events=events)


def _browser_should_yield_force_frame_rate() -> ScenarioResult:
    # Approximate upstream `unstable_forceFrameRate(60)` by setting `frame_yield_ms`.
    # Upstream uses ~16ms for 60fps.
    flags = SchedulerBrowserFlags()
    flags.frame_yield_ms = 16.0
    host = MockBrowserRuntime()
    harness = BrowserSchedulerHarness(host, flags=flags)

    def cb(_did_timeout: bool) -> None:
        harness.unstable_request_paint()  # no-op for this scenario (kept off by flags)
        while not harness.unstable_should_yield():
            host.advance_time(1.0)
        host.log(f"Yield at {int(host.performance.now())}ms")

    harness.unstable_schedule_callback(unstable_NormalPriority, cb)

    events: list[str] = []
    while host._has_pending_message:  # type: ignore[attr-defined]
        if host._event_log:  # type: ignore[attr-defined]
            events.extend(host._event_log)  # type: ignore[attr-defined]
            host._event_log = []  # type: ignore[attr-defined]
        host.fire_message_event()
        events.extend(host._event_log)  # type: ignore[attr-defined]
        host._event_log = []  # type: ignore[attr-defined]

    return ScenarioResult(name="browser.should_yield.force_frame_rate", events=events)
