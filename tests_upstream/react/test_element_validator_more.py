from __future__ import annotations

import warnings

import pytest
from ryact import create_element
from ryact.dev import set_dev
from ryact_testkit import create_noop_root


def test_does_not_warn_when_using_dom_node_as_children() -> None:
    # Upstream: ReactElementValidator-test.internal.js
    # "does not warn when using DOM node as children"
    set_dev(True)
    dom_node = {"nodeType": 1, "tagName": "DIV"}
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        create_element("div", {"children": (dom_node,)})
    assert rec == []


def test_gives_a_helpful_error_when_passing_invalid_types() -> None:
    # Upstream: ReactElementValidator-test.internal.js
    # "gives a helpful error when passing invalid types"
    set_dev(True)

    def Owner(**_: object) -> object:
        # Invalid element type: `None`
        return create_element(None)

    root = create_noop_root()
    with pytest.raises(TypeError) as exc:
        root.render(create_element(Owner))
    msg = str(exc.value).lower()
    assert "element type is invalid" in msg
    assert "null" in msg
    assert "component stack" in msg
    assert "in owner" in msg


def test_includes_the_owner_name_when_passing_null_undefined_boolean_or_number() -> None:
    # Upstream: ReactElementValidator-test.internal.js
    # "includes the owner name when passing null, undefined, boolean, or number"
    set_dev(True)

    def Owner(**_: object) -> object:
        return create_element(False)  # invalid type

    root = create_noop_root()
    with pytest.raises(TypeError) as exc:
        root.render(create_element(Owner))
    msg = str(exc.value).lower()
    assert "element type is invalid" in msg
    assert "bool" in msg or "boolean" in msg
    assert "in owner" in msg


def test_should_give_context_for_errors_in_nested_components() -> None:
    # Upstream: ReactElementValidator-test.internal.js
    # "should give context for errors in nested components."
    set_dev(True)

    def Inner(**_: object) -> object:
        return create_element(None)

    def Outer(**_: object) -> object:
        return create_element(Inner)

    root = create_noop_root()
    with pytest.raises(TypeError) as exc:
        root.render(create_element(Outer))
    msg = str(exc.value)
    assert "Component stack:" in msg
    assert "in Inner" in msg
    assert "in Outer" in msg
