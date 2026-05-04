# Upstream: packages/react/src/__tests__/ReactProfiler-test.internal.js
# May 2026 inventory slice: minimal profiler callback surface smoke.
from __future__ import annotations

from typing import Any

import pytest

from ryact import Component, create_element
from ryact.concurrent import profiler
from ryact_testkit import create_noop_root


def _span(text: str) -> Any:
    return create_element("span", {"text": text})


def test_profiler_is_called_on_mount_and_update_smoke() -> None:
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
    assert phases[0] == "mount"
    assert "update" in phases


def test_profiler_handles_errors_thrown_smoke() -> None:
    def on_render(*_a: object, **_k: object) -> None:
        return

    def Boom() -> Any:
        raise RuntimeError("x")

    root = create_noop_root()
    with pytest.raises(RuntimeError):
        root.render(profiler(id="p", on_render=on_render, children=create_element(Boom)))
        root.flush()

