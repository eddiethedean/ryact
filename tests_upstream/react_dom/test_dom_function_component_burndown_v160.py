# Translated from: packages/react-dom/src/__tests__/ReactFunctionComponent-test.js
# Burndown v160: stateless/function component DOM rendering.
from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest
from ryact import Component, create_element
from ryact.dev import is_dev, set_dev
from ryact.hooks import get_legacy_context
from ryact_dom.dom import Container
from ryact_dom.root import create_root
from ryact_testkit import WarningCapture


@pytest.fixture(autouse=True)
def _dev_on() -> Iterator[None]:
    prev = is_dev()
    set_dev(True)
    yield
    set_dev(prev)


def _text(container: Container) -> str:
    return container.text_content


def test_should_render_stateless_component() -> None:
    def FunctionComponent(**props: Any) -> object:
        return create_element("span", None, props["name"])

    c = Container()
    root = create_root(c)
    root.render(create_element(FunctionComponent, {"name": "A"}))
    assert _text(c) == "A"


def test_should_update_stateless_component() -> None:
    class Parent(Component):
        def render(self) -> object:
            return create_element(FunctionComponent, {"name": self.props["name"]})

    def FunctionComponent(**props: Any) -> object:
        return create_element("span", None, props["name"])

    c = Container()
    root = create_root(c)
    root.render(create_element(Parent, {"name": "A"}))
    assert _text(c) == "A"
    root.render(create_element(Parent, {"name": "B"}))
    assert _text(c) == "B"


def test_should_unmount_stateless_component() -> None:
    def FunctionComponent(**props: Any) -> object:
        return create_element("span", None, props["name"])

    c = Container()
    root = create_root(c)
    root.render(create_element(FunctionComponent, {"name": "A"}))
    assert _text(c) == "A"
    root.unmount()
    assert _text(c) == ""


def test_should_pass_context_thru_stateless_component() -> None:
    class Child(Component):
        def render(self) -> object:
            return create_element("span", None, str(self.context.get("test", "")))

    Child.contextTypes = {"test": object}  # type: ignore[attr-defined]

    def Parent() -> object:
        return create_element(Child)

    class GrandParent(Component):
        def getChildContext(self) -> dict[str, str]:  # noqa: N802
            return {"test": str(self.props["test"])}

        def render(self) -> object:
            return create_element(Parent)

    GrandParent.childContextTypes = {"test": object}  # type: ignore[attr-defined]

    c = Container()
    root = create_root(c)
    with WarningCapture():
        root.render(create_element(GrandParent, {"test": "test"}))
    assert _text(c) == "test"
    with WarningCapture():
        root.render(create_element(GrandParent, {"test": "mest"}))
    assert _text(c) == "mest"


def test_should_warn_for_getderivedstatefromprops_on_a_function_component() -> None:
    def FunctionComponentWithChildContext() -> object:
        return None

    FunctionComponentWithChildContext.getDerivedStateFromProps = lambda *_a: None  # type: ignore[attr-defined]

    c = Container()
    root = create_root(c)
    with WarningCapture() as cap:
        root.render(create_element(FunctionComponentWithChildContext))
    assert any(
        "Function components do not support getDerivedStateFromProps" in str(r.message) for r in cap.records
    )


def test_should_warn_for_childcontexttypes_on_a_function_component() -> None:
    def FunctionComponentWithChildContext(**props: Any) -> object:
        return create_element("span", None, props["name"])

    FunctionComponentWithChildContext.childContextTypes = {"foo": object}  # type: ignore[attr-defined]

    c = Container()
    root = create_root(c)
    with WarningCapture() as cap:
        root.render(create_element(FunctionComponentWithChildContext, {"name": "A"}))
    assert any("childContextTypes cannot be defined on a function component" in str(r.message) for r in cap.records)


def test_should_not_throw_when_stateless_component_returns_undefined() -> None:
    def NotAComponent() -> None:
        return None

    c = Container()
    root = create_root(c)
    root.render(create_element(NotAComponent))
    root.render(create_element("span", None, "ok"))
    assert _text(c) == "ok"


def test_should_use_correct_name_in_key_warning() -> None:
    def Child() -> object:
        return [
            create_element("span", None, "x"),
            create_element("span", None, "y"),
        ]

    c = Container()
    root = create_root(c)
    with WarningCapture() as cap:
        root.render(create_element(Child))
    assert any('Check the render method of `Child`' in str(r.message) for r in cap.records)


def test_should_receive_context() -> None:
    class Parent(Component):
        def getChildContext(self) -> dict[str, str]:  # noqa: N802
            return {"lang": "en"}

        def render(self) -> object:
            return create_element(Child)

    Parent.childContextTypes = {"lang": object}  # type: ignore[attr-defined]

    def Child(**_props: Any) -> object:
        lang = get_legacy_context().get("lang", "")
        return create_element("span", None, lang)

    Child.contextTypes = {"lang": object}  # type: ignore[attr-defined]

    c = Container()
    root = create_root(c)
    with WarningCapture():
        root.render(create_element(Parent))
    assert _text(c) == "en"


def test_should_work_with_arrow_functions() -> None:
    def Child() -> object:
        return create_element("span", None, "ok")

    bound = Child.__get__(object(), object())  # type: ignore[attr-defined]
    c = Container()
    root = create_root(c)
    root.render(create_element(bound))
    assert _text(c) == "ok"


def test_should_allow_simple_functions_to_return_null() -> None:
    def Child() -> None:
        return None

    c = Container()
    root = create_root(c)
    root.render(create_element(Child))
    assert _text(c) == ""


def test_should_allow_simple_functions_to_return_false() -> None:
    def Child() -> bool:
        return False

    c = Container()
    root = create_root(c)
    root.render(create_element(Child))
    assert _text(c) == ""
