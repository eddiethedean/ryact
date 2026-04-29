from __future__ import annotations

from ryact import (
    Component,
    StrictMode,
    context_provider,
    create_context,
    create_element,
    fragment,
    use_effect,
    use_layout_effect,
)
from ryact.dev import set_dev
from ryact_testkit import create_noop_root


def test_classes_and_functions_are_double_invoked_together_correctly() -> None:
    # Upstream: StrictEffectsMode-test.js — class cDM before sibling function layout/passive,
    # then strict replay (class + hooks).
    set_dev(True)
    try:
        log: list[str] = []

        class ClassChild(Component):
            def componentDidMount(self) -> None:  # noqa: N802
                log.append("componentDidMount")

            def componentWillUnmount(self) -> None:  # noqa: N802
                log.append("componentWillUnmount")

            def render(self) -> object:
                return self.props["text"]

        def FunctionChild(**props: object) -> object:
            text = props["text"]

            def eff() -> object:
                log.append("useEffect mount")

                def cleanup() -> None:
                    log.append("useEffect unmount")

                return cleanup

            def leff() -> object:
                log.append("useLayoutEffect mount")

                def cleanup() -> None:
                    log.append("useLayoutEffect unmount")

                return cleanup

            use_effect(eff, ())
            use_layout_effect(leff, ())
            return text

        def App(**props: object) -> object:
            text = props["text"]
            return create_element(
                StrictMode,
                None,
                fragment(
                    create_element(ClassChild, {"text": text, "key": "class"}),
                    create_element(FunctionChild, {"text": text, "key": "fn"}),
                ),
            )

        root = create_noop_root()
        root.render(create_element(App, {"text": "x"}))
        assert log == [
            "componentDidMount",
            "useLayoutEffect mount",
            "useEffect mount",
            "componentWillUnmount",
            "useLayoutEffect unmount",
            "useEffect unmount",
            "componentDidMount",
            "useLayoutEffect mount",
            "useEffect mount",
        ]

        log.clear()
        root.render(None)
        assert log == [
            "componentWillUnmount",
            "useLayoutEffect unmount",
            "useEffect unmount",
        ]
    finally:
        set_dev(False)


def test_passes_the_right_context_to_class_component_lifecycles() -> None:
    # Upstream: StrictEffectsMode-test.js — `this.test()` in each lifecycle (JavaScript
    # receiver / `this` context). In Python we call an instance method from each hook.
    set_dev(True)
    try:
        log: list[str] = []

        class App(Component):
            def mark(self) -> None:
                pass

            def componentDidMount(self) -> None:  # noqa: N802
                self.mark()
                log.append("componentDidMount")

            def componentDidUpdate(self) -> None:  # noqa: N802
                self.mark()
                log.append("componentDidUpdate")

            def componentWillUnmount(self) -> None:  # noqa: N802
                self.mark()
                log.append("componentWillUnmount")

            def render(self) -> object:
                return None

        create_noop_root().render(create_element(StrictMode, None, create_element(App)))
        assert log == ["componentDidMount", "componentWillUnmount", "componentDidMount"]
    finally:
        set_dev(False)


def test_context_provider_snapshot_for_class_lifecycles_under_strict_mode() -> None:
    # Extra coverage: React Context value is stable for class strict replay.
    set_dev(True)
    try:
        log: list[str] = []
        ctx = create_context("default")

        class Reader(Component):
            contextType = ctx

            def componentDidMount(self) -> None:  # noqa: N802
                log.append(f"didMount:{self.context}")

            def componentWillUnmount(self) -> None:  # noqa: N802
                log.append(f"willUnmount:{self.context}")

            def render(self) -> object:
                log.append(f"render:{self.context}")
                return create_element("div")

        tree = context_provider(
            ctx,
            "provided",
            create_element(StrictMode, None, create_element(Reader)),
        )
        create_noop_root().render(tree)
        assert log == [
            "render:provided",
            "render:provided",
            "didMount:provided",
            "willUnmount:provided",
            "didMount:provided",
        ]
    finally:
        set_dev(False)
