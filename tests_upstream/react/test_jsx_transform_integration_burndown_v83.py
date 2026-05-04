from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest
from ryact import (
    UNDEFINED,
    Component,
    Element,
    create_element,
    create_ref,
    jsx,
)
from ryact_testkit import create_noop_root


def test_allows_string_types_lower_and_upper_case() -> None:
    # Upstream: ReactJSXTransformIntegration-test.js
    assert jsx("div", {}).type == "div"
    assert jsx("ABC", {}).type == "ABC"


def test_allows_static_methods_via_element_type() -> None:
    # Upstream: "allows static methods to be called using the type property"
    class Foo(Component):
        @staticmethod
        def ping() -> str:
            return "pong"

        def render(self) -> object:
            return None

    el = jsx(Foo, {})
    assert el.type.ping() == "pong"  # type: ignore[union-attr]


def test_coerces_key_to_string() -> None:
    el = jsx("div", {"key": 123})
    assert el.key == "123"


def test_extracts_key_but_not_ref_from_rest_props() -> None:
    r = create_ref()
    el = jsx("div", {"key": "k", "ref": r, "data-x": 1})
    assert el.key == "k"
    assert el.ref is r
    assert "key" not in el.props
    assert "ref" not in el.props
    assert el.props["data-x"] == 1


def test_does_not_override_children_if_no_jsx_children_are_provided() -> None:
    el = jsx("div", {"children": ("a",)})
    assert el.props["children"] == ("a",)


def test_does_not_reuse_spread_props_object() -> None:
    config = {"foo": "foo"}
    el = jsx("div", config)
    backing = getattr(el.props, "_data", el.props)
    assert backing is not config


def test_merges_jsx_children_onto_children_prop_single_and_array() -> None:
    el1 = jsx("div", {}, "a")
    assert el1.props["children"] == ("a",)

    el2 = jsx("div", {}, "a", "b")
    assert el2.props["children"] == ("a", "b")


def test_overrides_children_if_null_provided_as_jsx_child() -> None:
    el = jsx("div", {"children": ("x",)}, None)
    assert el.props["children"] == (None,)


def test_overrides_children_if_undefined_provided_as_argument() -> None:
    el = jsx("div", {"children": ("x",)}, UNDEFINED)
    assert el.props["children"] == ()


def test_returns_a_complete_element_according_to_spec() -> None:
    r = create_ref()
    el = jsx("div", {"key": "k", "ref": r, "foo": "bar"}, "child")
    assert isinstance(el, Element)
    assert el.type == "div"
    assert el.key == "k"
    assert el.ref is r
    assert el.props["foo"] == "bar"
    assert el.props["children"] == ("child",)


def test_returns_an_immutable_element() -> None:
    el = jsx("div", {"foo": "bar"})
    with pytest.raises(FrozenInstanceError):
        # frozen dataclass should prevent mutation
        el.key = "x"  # type: ignore[misc]


def test_sanity_check_jsx_runtime_exists() -> None:
    # Upstream checks that JSX compiles to jsx(); our Python analogue is that `jsx` is callable.
    assert callable(jsx)


def test_default_props_normalization_and_removal() -> None:
    # Upstream:
    # - "should normalize props with default values"
    # - "should use default prop value when removing a prop"
    class C(Component):
        defaultProps = {"x": 1}

        def render(self) -> object:
            return create_element("span", {"children": [str(self.props["x"])]})

    root = create_noop_root()
    root.render(create_element(C, {}))
    assert "1" in str(root.get_children_snapshot())

    root.render(create_element(C, {"x": 2}))
    assert "2" in str(root.get_children_snapshot())

    root.render(create_element(C, {}))
    assert "1" in str(root.get_children_snapshot())
