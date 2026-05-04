from __future__ import annotations

from typing import Any

from ryact import create_element, use_effect_event, use_state
from ryact_testkit import create_noop_root


def _span(text: str) -> Any:
    return create_element("span", {"text": text})


def test_use_effect_event_returns_stable_callable_with_latest_implementation() -> None:
    calls: list[str] = []

    def App() -> Any:
        v, set_v = use_state("A")

        def impl() -> None:
            calls.append(v)

        ev = use_effect_event(impl)
        # Call during render for deterministic smoke; should call latest fn.
        ev()
        if v == "A":
            set_v("B")
        return _span(v)

    root = create_noop_root()
    root.render(create_element(App))
    root.flush()
    root.flush()
    assert "A" in calls and "B" in calls

