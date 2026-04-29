from __future__ import annotations

from ryact import create_element, use_effect
from ryact_testkit import act, create_noop_root, set_act_environment_enabled


def test_act_can_flush_effects() -> None:
    # Upstream: ReactNoopRendererAct-test.js — "can use act to flush effects"
    log: list[str] = []

    def App() -> object:
        def eff() -> None:
            log.append("effect")

        use_effect(eff, ())
        return create_element("div", {"text": "ok"})

    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        with act(flush=root.flush):
            root.render(create_element(App, {}))
    finally:
        set_act_environment_enabled(False)

    assert log == ["effect"]
    assert root.get_children_snapshot() == {
        "type": "div",
        "key": None,
        "props": {"text": "ok"},
        "children": [],
    }

