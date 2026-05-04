from __future__ import annotations

from collections.abc import Callable

from ryact import StrictMode, create_element, use_effect, use_layout_effect
from ryact.dev import set_dev
from ryact_testkit import create_noop_root


def test_multiple_effects_double_invoked_order_all_mounted_all_unmounted_all_remounted() -> None:
    # Upstream: StrictEffectsMode-test.js
    set_dev(True)
    try:
        log: list[str] = []

        def App() -> object:
            def eff_a() -> Callable[[], None] | None:
                log.append("mount:a")

                def cleanup() -> None:
                    log.append("cleanup:a")

                return cleanup

            def eff_b() -> Callable[[], None] | None:
                log.append("mount:b")

                def cleanup() -> None:
                    log.append("cleanup:b")

                return cleanup

            use_effect(eff_a, ())
            use_effect(eff_b, ())
            return create_element("div")

        create_noop_root().render(create_element(StrictMode, None, create_element(App)))
        assert log == ["mount:a", "mount:b", "cleanup:a", "cleanup:b", "mount:a", "mount:b"]
    finally:
        set_dev(False)


def test_multiple_layout_effects_double_invoked_order_all_mounted_all_unmounted_all_remounted() -> (
    None
):
    # Upstream: StrictEffectsMode-test.js
    set_dev(True)
    try:
        log: list[str] = []

        def App() -> object:
            def eff_a() -> Callable[[], None] | None:
                log.append("mount:a")

                def cleanup() -> None:
                    log.append("cleanup:a")

                return cleanup

            def eff_b() -> Callable[[], None] | None:
                log.append("mount:b")

                def cleanup() -> None:
                    log.append("cleanup:b")

                return cleanup

            use_layout_effect(eff_a, ())
            use_layout_effect(eff_b, ())
            return create_element("div")

        create_noop_root().render(create_element(StrictMode, None, create_element(App)))
        assert log == ["mount:a", "mount:b", "cleanup:a", "cleanup:b", "mount:a", "mount:b"]
    finally:
        set_dev(False)


def test_useeffect_and_uselayouteffect_called_twice_when_there_is_no_unmount() -> None:
    # Upstream: StrictEffectsMode-test.js
    set_dev(True)
    try:
        log: list[str] = []

        def App() -> object:
            def lay() -> Callable[[], None] | None:
                log.append("layout:mount")

                def cleanup() -> None:
                    log.append("layout:cleanup")

                return cleanup

            def pas() -> Callable[[], None] | None:
                log.append("passive:mount")

                def cleanup() -> None:
                    log.append("passive:cleanup")

                return cleanup

            use_layout_effect(lay, ())
            use_effect(pas, ())
            return create_element("div")

        create_noop_root().render(create_element(StrictMode, None, create_element(App)))
        assert log == [
            "layout:mount",
            "passive:mount",
            "layout:cleanup",
            "layout:mount",
            "passive:cleanup",
            "passive:mount",
        ]
    finally:
        set_dev(False)
