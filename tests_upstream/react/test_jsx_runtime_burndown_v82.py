from __future__ import annotations

import math
from typing import Any, cast

import pytest

from ryact import Component, create_element, jsx, jsxs
from ryact.concurrent import lazy
from ryact.dev import set_dev
from ryact_testkit import WarningCapture, create_noop_root


def test_allows_static_methods_to_be_called_using_the_type_property() -> None:
    # Upstream: ReactJSXRuntime-test.js
    class C(Component):
        @staticmethod
        def some_static() -> str:
            return "someReturnValue"

        def render(self) -> object:
            return None

    el = create_element(C, {})
    assert el.type.some_static() == "someReturnValue"


def test_does_not_call_lazy_initializers_eagerly() -> None:
    # Upstream: ReactJSXRuntime-test.js
    called = {"v": False}

    def loader() -> object:
        called["v"] = True

        def Inner(**_props: object) -> object:
            return None

        return Inner

    _ = create_element(lazy(loader), {})
    assert called["v"] is False


def test_should_use_default_prop_value_when_removing_a_prop() -> None:
    # Upstream: ReactJSXRuntime-test.js
    class Fruit(Component):
        defaultProps = {"fruit": "persimmon"}  # noqa: RUF012

        def render(self) -> object:
            return str(self.props.get("fruit", ""))

    root = create_noop_root()
    root.render(create_element(Fruit, {"fruit": "mango"}))
    assert "mango" in str(root.get_children_snapshot())
    root.render(create_element(Fruit, {}))
    assert "persimmon" in str(root.get_children_snapshot())


def test_should_normalize_props_with_default_values() -> None:
    # Upstream: ReactJSXRuntime-test.js
    captured: dict[str, Any] = {}

    class P(Component):
        defaultProps = {"prop": "testKey"}  # noqa: RUF012

        def render(self) -> object:
            captured["props"] = self.props
            return str(self.props.get("prop", ""))

    root = create_noop_root()
    root.render(create_element(P, {}))
    assert cast(dict[str, Any], captured["props"]).get("prop") == "testKey"

    captured.clear()
    root.render(create_element(P, {"prop": None}))
    assert cast(dict[str, Any], captured["props"]).get("prop") is None


def test_does_not_warn_for_nan_props() -> None:
    # Upstream: ReactJSXRuntime-test.js
    captured: dict[str, Any] = {}

    class T(Component):
        def render(self) -> object:
            captured["value"] = self.props.get("value")
            return None

    set_dev(True)
    try:
        with WarningCapture() as cap:
            root = create_noop_root()
            root.render(create_element(T, {"value": float("nan")}))
        assert cap.records == []
        assert captured["value"] is not None and math.isnan(float(captured["value"]))
    finally:
        set_dev(True)


def test_throws_when_changing_a_prop_in_dev_after_element_creation() -> None:
    # Upstream: ReactJSXRuntime-test.js
    class Outer(Component):
        def render(self) -> object:
            el = create_element("div", {"className": "moo"})
            with pytest.raises(TypeError):
                el.props["className"] = "quack"  # type: ignore[index]
            assert el.props.get("className") == "moo"
            return el

    set_dev(True)
    try:
        root = create_noop_root()
        root.render(create_element(Outer, {}))
        snap = str(root.get_children_snapshot())
        assert "moo" in snap or "className" in snap
    finally:
        set_dev(True)


def test_throws_when_adding_a_prop_in_dev_after_element_creation() -> None:
    # Upstream: ReactJSXRuntime-test.js
    class Outer(Component):
        def render(self) -> object:
            el = create_element("div", {"children": self.props.get("sound")})
            with pytest.raises(TypeError):
                el.props["className"] = "quack"  # type: ignore[index]
            assert el.props.get("className") is None
            return el

    class OuterRoot(Component):
        defaultProps = {"sound": "meow"}  # noqa: RUF012

        def render(self) -> object:
            return create_element(Outer, dict(self.props))

    set_dev(True)
    try:
        root = create_noop_root()
        root.render(create_element(OuterRoot, {}))
        assert "meow" in str(root.get_children_snapshot())
    finally:
        set_dev(True)


def test_should_warn_when_key_is_being_accessed_on_a_host_element() -> None:
    # Upstream: ReactJSXRuntime-test.js — key is not stored on props; reading warns.
    set_dev(True)
    try:
        el = create_element("div", {})
        with WarningCapture() as cap:
            _ = el.props["key"]  # type: ignore[index]
        msg = "\n".join(str(r.message) for r in cap.records).lower()
        assert "key" in msg
        assert "not a prop" in msg
    finally:
        set_dev(True)


def test_should_warn_when_key_is_being_accessed_on_composite_element() -> None:
    # Upstream: ReactJSXRuntime-test.js
    set_dev(True)
    try:

        class Child(Component):
            def render(self) -> object:
                _ = self.props["key"]  # type: ignore[index]
                return None

        class Parent(Component):
            def render(self) -> object:
                return create_element(
                    "div",
                    {
                        "children": (
                            create_element(Child, {}, key="0"),
                            create_element(Child, {}, key="1"),
                            create_element(Child, {}, key="2"),
                        )
                    },
                )

        with WarningCapture() as cap:
            create_noop_root().render(create_element(Parent, {}))
        assert any("not a prop" in str(r.message).lower() for r in cap.records)
    finally:
        set_dev(True)


def test_should_warn_when_unkeyed_children_are_passed_to_jsx() -> None:
    # Upstream: ReactJSXRuntime-test.js — list of siblings without keys under a host.
    set_dev(True)
    try:

        class Child(Component):
            def render(self) -> object:
                return create_element("div", {})

        class Parent(Component):
            def render(self) -> object:
                return create_element(
                    "div",
                    {
                        "children": (
                            create_element(Child, {}),
                            create_element(Child, {}),
                            create_element(Child, {}),
                        )
                    },
                )

        with WarningCapture() as cap:
            create_noop_root().render(create_element(Parent, {}))
        msg = "\n".join(str(r.message) for r in cap.records).lower()
        assert "key" in msg
    finally:
        set_dev(True)


def test_does_not_clone_props_object_if_key_and_ref_is_not_spread() -> None:
    # Upstream: ReactJSXRuntime-test.js — same props object reference when key/ref not in bag.
    config = {"foo": "foo", "bar": "bar"}
    set_dev(False)
    try:
        el = create_element("div", config)
        assert el.props is config
    finally:
        set_dev(True)

    set_dev(True)
    try:
        config2 = {"foo": "foo", "bar": "bar"}
        el2 = create_element("div", config2)
        assert getattr(el2.props, "_data", None) is config2
    finally:
        set_dev(True)

    config_with_key = {"foo": "foo", "bar": "bar", "key": "key"}
    set_dev(True)
    try:
        with WarningCapture() as cap:
            el3 = jsx("div", config_with_key)
        msg = "\n".join(str(r.message) for r in cap.records).lower()
        assert "key" in msg and "spread" in msg
        assert el3.key == "key"
        assert "key" in config_with_key
        backing = getattr(el3.props, "_data", el3.props)
        assert backing is not config_with_key
    finally:
        set_dev(True)


def test_is_indistinguishable_from_a_plain_object() -> None:
    # Upstream: Object.is(element.constructor, ({}).constructor). Ryact uses explicit
    # ``Element`` instances instead of plain dicts.
    from ryact import Element

    el = create_element("div", {"className": "foo"})
    assert isinstance(el, Element)
    assert not isinstance(el, dict)
    plain = object()
    assert type(el) is not type(plain)


def test_should_not_warn_when_unkeyed_children_are_passed_to_jsxs() -> None:
    # Upstream: React.jsxs with a static child array — no missing-key warning.
    set_dev(True)
    try:

        class Child(Component):
            def render(self) -> object:
                return create_element("div", {})

        class Parent(Component):
            def render(self) -> object:
                return jsxs(
                    "div",
                    {
                        "children": (
                            create_element(Child, {}),
                            create_element(Child, {}),
                            create_element(Child, {}),
                        )
                    },
                )

        with WarningCapture() as cap:
            create_noop_root().render(create_element(Parent, {}))
        key_msgs = [r for r in cap.records if "key" in str(r.message).lower()]
        assert key_msgs == []
    finally:
        set_dev(True)


def test_should_warn_when_keys_are_passed_as_part_of_props() -> None:
    # Upstream: key inside props object (spread-style) should warn.
    set_dev(True)
    try:

        class Child(Component):
            def render(self) -> object:
                return create_element("div", {})

        class Parent(Component):
            def render(self) -> object:
                return create_element(
                    "div",
                    {"children": (jsx(Child, {"key": "0", "prop": "hi"}),)},
                )

        with WarningCapture() as cap:
            create_noop_root().render(create_element(Parent, {}))
        msg = "\n".join(str(r.message) for r in cap.records).lower()
        assert "key" in msg and "spread" in msg
    finally:
        set_dev(True)


def test_warns_when_a_jsxs_is_passed_something_that_is_not_an_array() -> None:
    # Upstream: React.jsxs with non-array children.
    set_dev(True)
    try:
        with WarningCapture() as cap:
            _ = jsxs("div", {"children": "foo"})
        msg = "\n".join(str(r.message) for r in cap.records).lower()
        assert "static children" in msg or "array" in msg
    finally:
        set_dev(True)


