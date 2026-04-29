from __future__ import annotations

from ryact import Component, StrictMode, create_element
from ryact.dev import set_dev
from ryact_testkit import create_noop_root


def test_double_invoking_works_for_class_components() -> None:
    # Upstream: StrictEffectsMode-test.js
    # Expect a mount -> unmount -> mount style replay for newly mounted class components.
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

        create_noop_root().render(create_element(StrictMode, None, create_element(C)))
        assert log == ["didMount", "willUnmount", "didMount"]
    finally:
        set_dev(False)


def test_invokes_componentwillunmount_for_class_components_without_componentdidmount() -> None:
    # Upstream: StrictEffectsMode-test.js
    # Even if componentDidMount is not defined, strict replay should still invoke unmount once.
    set_dev(True)
    try:
        log: list[str] = []

        class C(Component):
            def componentWillUnmount(self) -> None:  # noqa: N802
                log.append("willUnmount")

            def render(self) -> object:
                return create_element("div")

        create_noop_root().render(create_element(StrictMode, None, create_element(C)))
        assert log == ["willUnmount"]
    finally:
        set_dev(False)


def test_classes_without_componentdidmount_and_functions_double_invoked_together_correctly() -> None:
    # Upstream: StrictEffectsMode-test.js
    # Ensure replay for a class (w/o cDM) doesn't block function component strict replay.
    set_dev(True)
    try:
        log: list[str] = []

        class C(Component):
            def componentWillUnmount(self) -> None:  # noqa: N802
                log.append("class:willUnmount")

            def render(self) -> object:
                return create_element("div")

        def Fn() -> object:
            log.append("fn:render")
            return create_element("span")

        create_noop_root().render(
            create_element(StrictMode, None, create_element("div", {"children": (create_element(C), create_element(Fn))}))
        )
        # Function mount render is double-invoked in StrictMode DEV (noop host surface).
        assert log.count("fn:render") == 2
        # Class unmount replay still happened.
        assert "class:willUnmount" in log
    finally:
        set_dev(False)

