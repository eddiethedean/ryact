from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ryact import create_element
from ryact.concurrent import activity, strict_mode
from ryact.dev import set_dev
from ryact_testkit import create_noop_root


def test_should_trigger_strict_effects_when_offscreen_is_visible() -> None:
    root = create_noop_root()
    set_dev(True)
    log: list[str] = []

    def Child(**_: Any) -> Any:
        from ryact import use_effect

        def eff() -> Callable[[], None] | None:
            log.append("mount")

            def cleanup() -> None:
                log.append("cleanup")

            return cleanup

        use_effect(eff, ())
        return create_element("div", {"id": "c"})

    root.render(
        strict_mode(
            create_element(activity, {"mode": "visible", "children": create_element(Child, {})})
        )
    )
    # Strict effects replay: mount, cleanup, mount.
    assert log == ["mount", "cleanup", "mount"]


def test_should_not_trigger_strict_effects_when_offscreen_is_hidden() -> None:
    root = create_noop_root()
    set_dev(True)
    log: list[str] = []

    def Child(**_: Any) -> Any:
        from ryact import use_effect

        def eff() -> Callable[[], None] | None:
            log.append("mount")
            return None

        use_effect(eff, ())
        return create_element("div", {"id": "c"})

    root.render(
        strict_mode(
            create_element(activity, {"mode": "hidden", "children": create_element(Child, {})})
        )
    )
    assert log == []


def test_double_invokes_effects_for_new_child_while_activity_becomes_visible() -> None:
    root = create_noop_root()
    set_dev(True)
    log: list[str] = []

    def Child(**_: Any) -> Any:
        from ryact import use_effect

        def eff() -> Callable[[], None] | None:
            log.append("mount")

            def cleanup() -> None:
                log.append("cleanup")

            return cleanup

        use_effect(eff, ())
        return create_element("div", {"id": "c"})

    # Start hidden.
    root.render(strict_mode(create_element(activity, {"mode": "hidden", "children": None})))
    assert log == []

    # Insert child while revealing: should strict-replay.
    root.render(
        strict_mode(
            create_element(activity, {"mode": "visible", "children": create_element(Child, {})})
        )
    )
    assert log == ["mount", "cleanup", "mount"]
