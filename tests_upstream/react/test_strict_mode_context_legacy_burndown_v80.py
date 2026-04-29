from __future__ import annotations

from collections.abc import Callable

from ryact import Component, StrictMode, create_element, use_effect
from ryact.dev import set_dev
from ryact_testkit import WarningCapture, create_noop_root


def test_should_warn_if_legacy_context_api_used_in_strict_mode() -> None:
    # Upstream: ReactStrictMode-test.js — context legacy
    set_dev(True)
    try:

        class LegacyContextProvider(Component):
            def getChildContext(self) -> dict[str, str]:  # noqa: N802
                return {"color": "purple"}

            def render(self) -> object:
                return create_element(
                    "div",
                    {
                        "children": (
                            create_element(LegacyContextConsumer, {"key": "a"}),
                            create_element(FunctionalLegacyContextConsumer, {"key": "b"}),
                        )
                    },
                )

        class LegacyContextConsumer(Component):
            def render(self) -> object:
                return None

        class Root(Component):
            def render(self) -> object:
                return create_element(StrictMode, None, create_element(LegacyContextProvider))

        def FunctionalLegacyContextConsumer() -> object:
            return None

        LegacyContextProvider.childContextTypes = {"color": None}
        LegacyContextConsumer.contextTypes = {"color": None}
        FunctionalLegacyContextConsumer.contextTypes = {"color": None}  # type: ignore[attr-defined]

        root = create_noop_root()
        with WarningCapture() as cap:
            root.render(create_element(Root))
        msgs = [str(r.message) for r in cap.records]
        assert any("LegacyContextProvider uses the legacy childContextTypes API" in m for m in msgs)
        assert any("LegacyContextConsumer uses the legacy contextTypes API" in m for m in msgs)
        assert any(
            "FunctionalLegacyContextConsumer uses the legacy contextTypes API" in m for m in msgs
        )
        assert any(
            "Legacy context API has been detected within a strict-mode tree" in m for m in msgs
        )

        with WarningCapture() as cap2:
            root.render(create_element(Root))
        assert len(cap2.records) == 0
    finally:
        set_dev(False)


def test_does_not_disable_logs_for_class_double_render() -> None:
    set_dev(True)
    try:
        count = 0
        logs: list[str] = []

        class Foo(Component):
            def render(self) -> object:
                nonlocal count
                count += 1
                logs.append(f"foo {count}")
                return None

        root = create_noop_root()
        root.render(create_element(StrictMode, None, create_element(Foo)))
        assert count == 2
        assert logs == ["foo 1", "foo 2"]
    finally:
        set_dev(False)


def test_does_not_disable_logs_for_class_double_ctor() -> None:
    set_dev(True)
    try:
        count = 0
        logs: list[str] = []

        class Foo(Component):
            def __init__(self, **props: object) -> None:
                super().__init__(**props)
                nonlocal count
                count += 1
                logs.append(f"foo {count}")

            def render(self) -> object:
                return None

        root = create_noop_root()
        root.render(create_element(StrictMode, None, create_element(Foo)))
        assert count == 2
        assert logs == ["foo 1", "foo 2"]
    finally:
        set_dev(False)


def test_does_not_disable_logs_for_class_double_getderivedstatefromprops() -> None:
    set_dev(True)
    try:
        count = 0
        logs: list[str] = []

        class Foo(Component):
            state: dict[str, object] = {}

            @staticmethod
            def getDerivedStateFromProps(_props: object, _state: object) -> dict[str, object]:  # noqa: N802
                nonlocal count
                count += 1
                logs.append(f"foo {count}")
                return {}

            def render(self) -> object:
                return None

        root = create_noop_root()
        root.render(create_element(StrictMode, None, create_element(Foo)))
        assert count == 2
        assert logs == ["foo 1", "foo 2"]
    finally:
        set_dev(False)


def test_does_not_disable_logs_for_class_double_shouldcomponentupdate() -> None:
    set_dev(True)
    try:
        count = 0
        logs: list[str] = []

        class Foo(Component):
            state: dict[str, object] = {}

            def shouldComponentUpdate(self, _next_props: object, _next_state: object) -> bool:  # noqa: N802
                nonlocal count
                count += 1
                logs.append(f"foo {count}")
                return True

            def render(self) -> object:
                return None

        root = create_noop_root()
        root.render(create_element(StrictMode, None, create_element(Foo)))
        root.render(create_element(StrictMode, None, create_element(Foo)))
        assert count == 2
        assert logs == ["foo 1", "foo 2"]
    finally:
        set_dev(False)


def test_does_not_disable_logs_for_class_state_updaters() -> None:
    set_dev(True)
    try:
        inst_holder: dict[str, Component] = {}
        count = 0
        logs: list[str] = []

        class Foo(Component):
            state: dict[str, object] = {}

            def render(self) -> object:
                inst_holder["i"] = self
                return None

        root = create_noop_root()
        root.render(create_element(StrictMode, None, create_element(Foo)))
        root.flush()
        inst = inst_holder["i"]

        def _patch(
            _s: object,
            _p: object,
        ) -> dict[str, object]:
            nonlocal count
            count += 1
            logs.append(f"foo {count}")
            return {}

        inst.set_state(_patch)
        root.flush()
        assert count == 2
        assert logs == ["foo 1", "foo 2"]
    finally:
        set_dev(False)


def test_does_not_disable_logs_for_function_double_render() -> None:
    set_dev(True)
    try:
        count = 0
        logs: list[str] = []

        def Foo() -> object:
            nonlocal count
            count += 1
            logs.append(f"foo {count}")
            return None

        root = create_noop_root()
        root.render(create_element(StrictMode, None, create_element(Foo)))
        assert count == 2
        assert logs == ["foo 1", "foo 2"]
    finally:
        set_dev(False)


def test_does_not_disable_logs_for_effect_double_invoke() -> None:
    set_dev(True)
    try:
        create = 0
        cleanup = 0
        logs: list[str] = []

        def Foo() -> object:
            def effect() -> Callable[[], None]:
                nonlocal create
                create += 1
                logs.append(f"foo create {create}")

                def _cleanup() -> None:
                    nonlocal cleanup
                    cleanup += 1
                    logs.append(f"foo cleanup {cleanup}")

                return _cleanup

            use_effect(effect)
            return None

        root = create_noop_root()
        root.render(create_element(StrictMode, None, create_element(Foo)))
        root.flush()
        assert create == 2
        assert cleanup == 1
        assert logs == ["foo create 1", "foo cleanup 1", "foo create 2"]
    finally:
        set_dev(False)
