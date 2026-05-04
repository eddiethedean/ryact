from __future__ import annotations

from ryact import StrictMode, create_element
from ryact.component import Component
from ryact.dev import set_dev
from ryact_testkit import WarningCapture, create_noop_root


def _warnings_containing(cap: WarningCapture, needle: str) -> list[str]:
    token = f"`{needle}`"
    out: list[str] = []
    for r in cap.records:
        msg = str(r.message)
        if token in msg:
            out.append(msg)
    return out


def test_should_also_warn_inside_of_strict_mode_trees() -> None:
    # Upstream: ReactStrictMode-test.js (Concurrent Mode)
    set_dev(True)
    try:

        class Foo(Component):
            def UNSAFE_componentWillReceiveProps(self) -> None:  # noqa: N802
                return None

            def render(self) -> object:
                return None

        class Bar(Component):
            def UNSAFE_componentWillReceiveProps(self) -> None:  # noqa: N802
                return None

            def render(self) -> object:
                return None

        def App() -> object:
            return create_element(
                StrictMode,
                None,
                create_element("div", {"children": (create_element(Foo), create_element(Bar))}),
            )

        with WarningCapture() as cap:
            create_noop_root().render(create_element(App))
        msgs = _warnings_containing(cap, "UNSAFE_componentWillReceiveProps")
        assert len(msgs) == 1
        assert "Foo" in msgs[0] and "Bar" in msgs[0]
    finally:
        set_dev(False)


def test_should_coalesce_warnings_by_lifecycle_name() -> None:
    # Upstream: ReactStrictMode-test.js (Concurrent Mode)
    set_dev(True)
    try:

        class App(Component):
            def UNSAFE_componentWillMount(self) -> None:  # noqa: N802
                return None

            def UNSAFE_componentWillUpdate(self) -> None:  # noqa: N802
                return None

            def render(self) -> object:
                return None

        class Parent(Component):
            def componentWillMount(self) -> None:  # noqa: N802
                return None

            def componentWillUpdate(self) -> None:  # noqa: N802
                return None

            def componentWillReceiveProps(self) -> None:  # noqa: N802
                return None

            def render(self) -> object:
                return None

        class Child(Component):
            def UNSAFE_componentWillReceiveProps(self) -> None:  # noqa: N802
                return None

            def render(self) -> object:
                return None

        def StrictRoot() -> object:
            return create_element(
                StrictMode,
                None,
                create_element(
                    "div",
                    {
                        "children": (
                            create_element(App),
                            create_element(Parent),
                            create_element(Child),
                        )
                    },
                ),
            )

        with WarningCapture() as cap:
            create_noop_root().render(create_element(StrictRoot))
        # One warning per lifecycle name, listing components that introduced it.
        assert len(_warnings_containing(cap, "UNSAFE_componentWillMount")) == 1
        assert len(_warnings_containing(cap, "UNSAFE_componentWillUpdate")) == 1
        assert len(_warnings_containing(cap, "UNSAFE_componentWillReceiveProps")) == 1
        assert len(_warnings_containing(cap, "componentWillMount")) == 1
        assert len(_warnings_containing(cap, "componentWillUpdate")) == 1
        assert len(_warnings_containing(cap, "componentWillReceiveProps")) == 1
    finally:
        set_dev(False)


def test_should_warn_about_components_not_present_during_the_initial_render() -> None:
    # Upstream: ReactStrictMode-test.js (Concurrent Mode)
    set_dev(True)
    try:

        class Foo(Component):
            def UNSAFE_componentWillMount(self) -> None:  # noqa: N802
                return None

            def render(self) -> object:
                return None

        class Bar(Component):
            def UNSAFE_componentWillMount(self) -> None:  # noqa: N802
                return None

            def render(self) -> object:
                return None

        def StrictRoot(*, foo: bool) -> object:
            child = create_element(Foo) if foo else create_element(Bar)
            return create_element(StrictMode, None, child)

        root = create_noop_root()
        with WarningCapture() as cap:
            root.render(create_element(StrictRoot, {"foo": True}))
        msgs = _warnings_containing(cap, "UNSAFE_componentWillMount")
        assert len(msgs) == 1
        assert "Foo" in msgs[0]

        with WarningCapture() as cap2:
            root.render(create_element(StrictRoot, {"foo": False}))
        msgs2 = _warnings_containing(cap2, "UNSAFE_componentWillMount")
        assert len(msgs2) == 1
        assert "Bar" in msgs2[0]
    finally:
        set_dev(False)
