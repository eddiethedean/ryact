from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ryact import create_element
from ryact.component import Component
from ryact.concurrent import activity
from ryact_testkit import create_noop_root
from ryact_testkit.warnings import WarningCapture


def test_mounts_without_effects_when_hidden() -> None:
    root = create_noop_root()
    log: list[str] = []

    def Child(**_: Any) -> Any:
        from ryact import use_effect, use_layout_effect

        def eff() -> Callable[[], None] | None:
            log.append("passive mount")

            def cleanup() -> None:
                log.append("passive cleanup")

            return cleanup

        def leff() -> Callable[[], None] | None:
            log.append("layout mount")

            def cleanup() -> None:
                log.append("layout cleanup")

            return cleanup

        use_layout_effect(leff, ())
        use_effect(eff, ())
        return create_element("div", {"id": "child"})

    root.render(create_element(activity, {"mode": "hidden", "children": create_element(Child, {})}))
    assert root.get_children_snapshot() is None
    assert log == []


def test_reveal_runs_effects_after_being_hidden() -> None:
    root = create_noop_root()
    log: list[str] = []

    def Child(**_: Any) -> Any:
        from ryact import use_effect

        def eff() -> Callable[[], None] | None:
            log.append("mount")
            return None

        use_effect(eff, ())
        return create_element("div", {"id": "child"})

    root.render(create_element(activity, {"mode": "hidden", "children": create_element(Child, {})}))
    assert log == []
    root.render(create_element(activity, {"mode": "visible", "children": create_element(Child, {})}))
    assert log == ["mount"]


def test_hiding_disconnects_effects_without_unmounting_component_instance() -> None:
    root = create_noop_root()
    log: list[str] = []

    def Child(**_: Any) -> Any:
        from ryact import use_effect

        def eff() -> Callable[[], None] | None:
            log.append("mount")

            def cleanup() -> None:
                log.append("cleanup")

            return cleanup

        use_effect(eff, ())
        return create_element("div", {"id": "child"})

    root.render(create_element(activity, {"mode": "visible", "children": create_element(Child, {})}))
    assert log == ["mount"]
    root.render(create_element(activity, {"mode": "hidden", "children": create_element(Child, {})}))
    # Cleanup should run when the tree becomes hidden.
    assert log == ["mount", "cleanup"]
    # Revealing should mount again.
    root.render(create_element(activity, {"mode": "visible", "children": create_element(Child, {})}))
    assert log == ["mount", "cleanup", "mount"]


def test_hidden_does_not_run_component_did_update_on_reappear() -> None:
    root = create_noop_root()
    log: list[str] = []

    class C(Component[dict[str, Any]]):
        def render(self) -> Any:
            return create_element("div", {"id": "c"})

        def componentDidUpdate(self) -> None:  # noqa: N802
            log.append("didUpdate")

    root.render(create_element(activity, {"mode": "visible", "children": create_element(C, {})}))
    root.render(create_element(activity, {"mode": "hidden", "children": create_element(C, {})}))
    root.render(create_element(activity, {"mode": "visible", "children": create_element(C, {})}))
    assert log == []


def test_class_setstate_callback_deferred_until_visible_commit() -> None:
    root = create_noop_root()
    log: list[str] = []
    sink: dict[str, Any] = {}

    class C(Component[dict[str, Any]]):
        def render(self) -> Any:
            sink["inst"] = self
            return create_element("div", {"id": "c"})

    root.render(create_element(activity, {"mode": "hidden", "children": create_element(C, {})}))
    inst = sink.get("inst")
    assert isinstance(inst, C)

    inst.setState({"x": 1}, lambda: log.append("cb"))
    # Still hidden, so callback should not have fired.
    assert log == []

    root.render(create_element(activity, {"mode": "visible", "children": create_element(C, {})}))
    assert log == ["cb"]


def test_warns_if_you_pass_a_hidden_prop() -> None:
    # Placeholder translation slice: we interpret passing a raw `hidden` prop as a DEV warning.
    # This will be tightened as we translate the upstream wording/stack expectations.
    root = create_noop_root()

    with WarningCapture() as wc:
        root.render(
            create_element(
                activity,
                {
                    "hidden": True,
                    "mode": "visible",
                    "children": create_element("div", {"id": "x"}),
                },
            )
        )
    assert any("hidden" in m for m in wc.messages)
