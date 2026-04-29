from __future__ import annotations

from typing import Any

from ryact import create_element
from ryact.concurrent import profiler
from ryact_testkit import create_noop_root


def _span(value: str) -> Any:
    return create_element("span", {"text": value})


def test_profiler_is_not_invoked_until_commit_phase() -> None:
    # Upstream: ReactProfiler-test.internal.js
    # "is not invoked until the commit phase"
    events: list[str] = []

    def on_render(id_: str, phase: str, *_: object) -> None:
        events.append(f"onRender:{id_}:{phase}")

    def App() -> Any:
        events.append("render")
        # If onRender ran during render, it would already be in `events`.
        assert events == ["render"]
        return _span("Hi")

    root = create_noop_root()
    root.render(profiler(id="p", on_render=on_render, children=create_element(App)))
    root.flush()

    assert events == ["render", "onRender:p:mount"]


def test_profiler_reports_mount_then_update_phase() -> None:
    # Upstream: ReactProfiler-test.internal.js
    # (subset of) "logs render times for both mount and update"
    phases: list[str] = []

    def on_render(_id: str, phase: str, *_: object) -> None:
        phases.append(phase)

    def App(*, value: str) -> Any:
        return _span(value)

    root = create_noop_root()
    root.render(profiler(id="p", on_render=on_render, children=create_element(App, {"value": "A"})))
    root.flush()
    root.render(profiler(id="p", on_render=on_render, children=create_element(App, {"value": "B"})))
    root.flush()

    assert phases == ["mount", "update"]

