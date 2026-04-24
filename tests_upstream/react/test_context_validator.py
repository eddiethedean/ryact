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
