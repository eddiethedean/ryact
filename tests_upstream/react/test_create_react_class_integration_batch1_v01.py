from __future__ import annotations

from typing import Any

import pytest

from ryact import create_element
from ryact.create_react_class import create_react_class
from ryact_testkit import create_noop_root


def test_throws_when_render_is_not_specified() -> None:
    with pytest.raises(TypeError):
        create_react_class({})


def test_throws_with_non_object_getinitialstate_return_values() -> None:
    C = create_react_class(
        {
            "render": lambda self: None,
            "getInitialState": lambda self: 123,
        }
    )
    root = create_noop_root()
    with pytest.raises(TypeError):
        root.render(create_element(C))
        root.flush()


def test_works_with_null_getinitialstate_return_value() -> None:
    C = create_react_class(
        {
            "render": lambda self: create_element("div", {"text": "ok"}),
            "getInitialState": lambda self: None,
        }
    )
    root = create_noop_root()
    root.render(create_element(C))
    root.flush()
    assert root.get_children_snapshot()["props"]["text"] == "ok"


def test_works_with_object_getinitialstate_return_values() -> None:
    C = create_react_class(
        {
            "render": lambda self: create_element("div", {"text": str(self.state.get("x"))}),
            "getInitialState": lambda self: {"x": 7},
        }
    )
    root = create_noop_root()
    root.render(create_element(C))
    root.flush()
    assert root.get_children_snapshot()["props"]["text"] == "7"


def test_supports_statics_and_prop_types() -> None:
    C = create_react_class(
        {
            "render": lambda self: None,
            "propTypes": {"foo": object()},
            "statics": {"answer": 42},
        }
    )
    assert getattr(C, "answer") == 42
    assert isinstance(getattr(C, "propTypes"), dict)


def test_throws_if_reserved_property_is_in_statics() -> None:
    with pytest.raises(TypeError):
        create_react_class({"render": lambda self: None, "statics": {"render": lambda: None}})


def test_throws_on_invalid_child_context_types() -> None:
    with pytest.raises(TypeError):
        create_react_class({"render": lambda self: None, "childContextTypes": 123})


def test_supports_getchildcontext_method_surface() -> None:
    # The noop reconciler uses getChildContext during child reconciliation; this is just
    # a smoke test that the method can be installed.
    C = create_react_class(
        {
            "render": lambda self: create_element("div", {"text": "ok"}),
            "getChildContext": lambda self: {"foo": 1},
            "childContextTypes": {"foo": object()},
        }
    )
    assert callable(getattr(C, "getChildContext"))

