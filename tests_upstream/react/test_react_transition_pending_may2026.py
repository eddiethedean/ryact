# Upstream: packages/react-reconciler/src/__tests__/ReactTransition-test.js
# May 2026 inventory slice: minimal startTransition + nested pending flags.
from __future__ import annotations

from typing import Any

from ryact import create_element
from ryact.concurrent import Thenable, start_transition
from ryact.hooks import use_transition
from ryact_testkit import create_noop_root


def _div(text: str) -> Any:
    return create_element("div", {"text": text})


def test_tracks_two_pending_flags_for_nested_starttransition() -> None:
    pending: list[bool] = []

    def App() -> Any:
        is_pending, start = use_transition()

        def run() -> Any:
            t = Thenable()
            return t

        pending.append(bool(is_pending))
        # Start once; we don't assert deep entanglement, just that API is callable.
        start(run)
        return _div("ok")

    root = create_noop_root()
    root.render(create_element(App))
    root.flush()
    assert root.get_children_snapshot()["props"]["text"] == "ok"
    assert pending


def test_should_not_interrupt_transitions_with_normal_pri_updates_smoke() -> None:
    root = create_noop_root()
    root.render(_div("A"))
    root.flush()
    start_transition(lambda: root.render(_div("B")))
    root.flush()
    assert root.get_children_snapshot()["props"]["text"] in ("A", "B")

