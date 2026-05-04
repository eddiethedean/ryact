from __future__ import annotations

from ryact import Component, create_context, create_element
from ryact.dev import set_dev
from ryact_testkit import WarningCapture, create_noop_root


def test_should_not_warn_when_class_contexttype_is_null() -> None:
    # Upstream: ReactContextValidator-test.js
    set_dev(True)
    root = create_noop_root()

    class App(Component):
        contextType = None

        def render(self) -> object:
            return create_element("div")

    with WarningCapture() as cap:
        root.render(create_element(App))
    assert cap.records == []


def test_should_warn_if_an_invalid_contexttype_is_defined() -> None:
    # Upstream: ReactContextValidator-test.js
    set_dev(True)
    root = create_noop_root()

    class App(Component):
        contextType = 123

        def render(self) -> object:
            return create_element("div")

    with WarningCapture() as cap:
        root.render(create_element(App))
    assert any("invalid contexttype" in str(r.message).lower() for r in cap.records)


def test_valid_contexttype_does_not_warn() -> None:
    set_dev(True)
    root = create_noop_root()
    Ctx = create_context("A")

    class App(Component):
        contextType = Ctx

        def render(self) -> object:
            return create_element("div")

    with WarningCapture() as cap:
        root.render(create_element(App))
    assert cap.records == []


def test_should_warn_if_both_contexttype_and_contexttypes_are_defined() -> None:
    # Upstream: ReactContextValidator-test.js
    # "should warn if both contextType and contextTypes are defined"
    set_dev(True)
    root = create_noop_root()
    Ctx = create_context("A")

    class App(Component):
        contextType = Ctx
        contextTypes = {"legacy": object()}

        def render(self) -> object:
            return create_element("div")

    with WarningCapture() as cap:
        root.render(create_element(App))
    assert any("both contexttype and contexttypes" in str(r.message).lower() for r in cap.records)


def test_should_warn_if_you_define_contexttype_on_a_function_component() -> None:
    # Upstream: ReactContextValidator-test.js
    # "should warn if you define contextType on a function component"
    set_dev(True)
    root = create_noop_root()
    Ctx = create_context("A")

    def App(**_: object) -> object:
        return create_element("div")

    # React warns if you attach this property to a function component.
    App.contextType = Ctx  # ty: ignore[unresolved-attribute]

    with WarningCapture() as cap:
        root.render(create_element(App))
    assert any("function component" in str(r.message).lower() for r in cap.records)


def test_should_warn_but_not_error_if_getchildcontext_method_is_missing() -> None:
    # Upstream: ReactContextValidator-test.js
    # "should warn (but not error) if getChildContext method is missing"
    set_dev(True)
    root = create_noop_root()

    class App(Component):
        childContextTypes = {"x": object()}

        def render(self) -> object:
            return create_element("div")

    with WarningCapture() as cap:
        root.render(create_element(App))
    assert any("getchildcontext" in str(r.message).lower() for r in cap.records)
