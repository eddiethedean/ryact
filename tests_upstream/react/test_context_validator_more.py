from __future__ import annotations

from ryact import Component, create_context, create_element
from ryact.dev import set_dev
from ryact_testkit import WarningCapture, create_noop_root


def test_should_warn_if_both_contexttype_and_contexttypes_are_defined() -> None:
    # Upstream: ReactContextValidator-test.js
    # "should warn if both contextType and contextTypes are defined"
    set_dev(True)
    Ctx = create_context("x")

    class App(Component):
        contextType = Ctx
        contextTypes = {"x": object()}

        def render(self) -> object:
            return create_element("div")

    with WarningCapture() as cap:
        create_noop_root().render(create_element(App))
    assert any("both contexttype and contexttypes" in str(r.message).lower() for r in cap.records)


def test_should_warn_if_you_define_contexttype_on_a_function_component() -> None:
    # Upstream: ReactContextValidator-test.js
    # "should warn if you define contextType on a function component"
    set_dev(True)
    Ctx = create_context("x")

    def App(**_: object) -> object:
        return create_element("div")

    App.contextType = Ctx  # ty: ignore[unresolved-attribute]
    with WarningCapture() as cap:
        create_noop_root().render(create_element(App))
    assert any("contexttype cannot be defined on a function component" in str(r.message).lower() for r in cap.records)


def test_should_warn_when_class_contexttype_is_a_primitive() -> None:
    # Upstream: ReactContextValidator-test.js
    # "should warn when class contextType is a primitive"
    set_dev(True)

    class App(Component):
        contextType = 1

        def render(self) -> object:
            return create_element("div")

    with WarningCapture() as cap:
        create_noop_root().render(create_element(App))
    assert any("invalid contexttype" in str(r.message).lower() for r in cap.records)


def test_should_warn_when_class_contexttype_is_an_object() -> None:
    # Upstream: ReactContextValidator-test.js
    # "should warn when class contextType is an object"
    set_dev(True)

    class App(Component):
        contextType = {"not": "a context"}

        def render(self) -> object:
            return create_element("div")

    with WarningCapture() as cap:
        create_noop_root().render(create_element(App))
    assert any("invalid contexttype" in str(r.message).lower() for r in cap.records)


def test_should_warn_when_class_contexttype_is_undefined() -> None:
    # Upstream: ReactContextValidator-test.js
    # "should warn when class contextType is undefined"
    set_dev(True)

    class App(Component):
        contextType = "undefined"

        def render(self) -> object:
            return create_element("div")

    with WarningCapture() as cap:
        create_noop_root().render(create_element(App))
    assert any("invalid contexttype" in str(r.message).lower() for r in cap.records)


def test_should_warn_but_not_error_if_getchildcontext_method_is_missing() -> None:
    # Upstream: ReactContextValidator-test.js
    # "should warn (but not error) if getChildContext method is missing"
    set_dev(True)

    class App(Component):
        childContextTypes = {"x": object()}

        def render(self) -> object:
            return create_element("div")

    with WarningCapture() as cap:
        create_noop_root().render(create_element(App))
    assert any("getchildcontext" in str(r.message).lower() for r in cap.records)
