from __future__ import annotations

from typing import Any

from ryact import create_element, use_effect, use_effect_event, use_state
from ryact_testkit import act, create_noop_root, set_act_environment_enabled


def _span(text: str) -> Any:
    return create_element("span", {"text": text})


def test_use_effect_event_forwards_to_latest_implementation_outside_render() -> None:
    calls: list[str] = []

    def App() -> Any:
        step, set_step = use_state(0)
        label = ("A", "B")[step]
        ev = use_effect_event(lambda: calls.append(label))

        def run() -> None:
            ev()
            if step == 0:
                set_step(1)

        use_effect(run, (step,))
        return _span(label)

    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        with act(flush=root.flush):
            root.render(create_element(App))
        root.flush()
        assert "A" in calls and "B" in calls
    finally:
        set_act_environment_enabled(False)
