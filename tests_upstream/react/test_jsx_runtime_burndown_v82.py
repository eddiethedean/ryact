from __future__ import annotations

import math
from typing import Any, cast

import pytest

from ryact import Component, create_element
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

