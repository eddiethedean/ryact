from __future__ import annotations

from collections.abc import Callable

from ryact import Component, StrictMode, create_element, use_effect
from ryact.dev import set_dev
from ryact_testkit import create_noop_root


def test_should_not_double_invoke_effects_in_legacy_mode() -> None:
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

        root = create_noop_root(legacy=True)
        root.render(create_element(StrictMode, None, create_element(App)))
        assert log == ["mount"]
    finally:
        set_dev(False)


def test_should_not_double_invoke_class_lifecycles_in_legacy_mode() -> None:
    # Upstream: StrictEffectsMode-test.js
    set_dev(True)
    try:
        log: list[str] = []

        class C(Component):
            def componentDidMount(self) -> None:  # noqa: N802
                log.append("didMount")

            def componentWillUnmount(self) -> None:  # noqa: N802
                log.append("willUnmount")

            def render(self) -> object:
                return create_element("div")

        root = create_noop_root(legacy=True)
        root.render(create_element(StrictMode, None, create_element(C)))
        assert log == ["didMount"]
        root.render(None)
        assert log == ["didMount", "willUnmount"]
    finally:
        set_dev(False)
