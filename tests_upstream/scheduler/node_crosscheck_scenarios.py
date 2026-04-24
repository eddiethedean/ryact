from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from schedulyr import (
    BrowserSchedulerHarness,
    MockBrowserRuntime,
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
    ]


def run_scenario(name: str) -> ScenarioResult:
    if name == "browser.basic_event_log":
        return _browser_basic_event_log()
    if name == "mock.basic_yield_log":
        return _mock_basic_yield_log()
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
