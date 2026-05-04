from __future__ import annotations

from collections.abc import Callable

from ryact import StrictMode, create_element, use_effect
from ryact.dev import set_dev
from ryact_testkit import create_noop_root


def test_double_invoking_for_effects_works_properly() -> None:
    # Upstream: StrictEffectsMode-test.js
    set_dev(True)
    try:
        log: list[str] = []

        def App() -> object:
            def eff() -> Callable[[], None] | None:
                log.append("mount")

                def cleanup() -> None:
                    log.append("cleanup")

                return cleanup

            use_effect(eff, ())
            return create_element("div")

        create_noop_root().render(create_element(StrictMode, None, create_element(App)))
        assert log == ["mount", "cleanup", "mount"]
    finally:
        set_dev(False)


def test_newly_mounted_components_after_initial_mount_get_double_invoked() -> None:
    # Upstream: StrictEffectsMode-test.js
    set_dev(True)
    try:
        log: list[str] = []
        root = create_noop_root()

        def Child() -> object:
            def eff() -> Callable[[], None] | None:
                log.append("child:mount")

                def cleanup() -> None:
                    log.append("child:cleanup")

                return cleanup

            use_effect(eff, ())
            return create_element("span")

        def App(*, show: bool) -> object:
            return create_element(
                "div", {"children": (create_element(Child, {}) if show else None,)}
            )

        root.render(create_element(StrictMode, None, create_element(App, {"show": False})))
        assert log == []

        root.render(create_element(StrictMode, None, create_element(App, {"show": True})))
        assert log == ["child:mount", "child:cleanup", "child:mount"]
    finally:
        set_dev(False)
