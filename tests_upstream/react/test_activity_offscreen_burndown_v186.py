# Translated from: packages/react-reconciler/src/__tests__/Activity-test.js
# Burndown v186: insertion effects stay connected across Activity visibility toggles.
from __future__ import annotations

from typing import Any

from ryact import activity, create_element, use_insertion_effect, use_memo
from ryact_testkit import act, create_noop_root, set_act_environment_enabled


def test_insertion_effects_are_not_disconnected_when_visibility_changes() -> None:
    log: list[str] = []

    def Child(props: dict[str, Any]) -> object:
        step = props["step"]

        def effect() -> Any:
            log.append(f"Commit mount [{step}]")

            def cleanup() -> None:
                log.append(f"Commit unmount [{step}]")

            return cleanup

        use_insertion_effect(effect, (step,))
        return create_element("span", {"text": str(step)})

    def App(props: dict[str, Any]) -> object:
        show = props["show"]
        step = props["step"]
        child = use_memo(lambda: create_element(Child, {"step": step}), (step,))
        return activity(children=child, mode="visible" if show else "hidden")

    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        with act(flush=root.flush):
            root.render(create_element(App, {"show": True, "step": 1}))
        assert log == ["Commit mount [1]"]
        snap = root.get_children_snapshot()
        assert snap is not None

        log.clear()
        with act(flush=root.flush):
            root.render(create_element(App, {"show": False, "step": 1}))
        assert log == []

        log.clear()
        with act(flush=root.flush):
            root.render(create_element(App, {"show": False, "step": 2}))
        assert log == ["Commit unmount [1]", "Commit mount [2]"]

        log.clear()
        with act(flush=root.flush):
            root.render(create_element(App, {"show": True, "step": 2}))
        assert log == []
    finally:
        set_act_environment_enabled(False)
