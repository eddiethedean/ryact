"""ReactDOMInput-test.js parity: Symbol/function values, defaultValue host, coercion (v129)."""

from __future__ import annotations

import warnings

import pytest
from ryact import create_element
from ryact.dev import is_dev
from ryact_dom.dom import Container, ElementNode
from ryact_dom.root import create_root


def _noop(_e: object) -> None:
    return None


def _host(c: Container) -> ElementNode:
    h = c.root.children[0]
    assert isinstance(h, ElementNode)
    return h


class Symbol:  # noqa: A001
    pass


class TemporalLike:
    def valueOf(self) -> object:
        raise TypeError("prod message")

    def __str__(self) -> str:
        return "2020-01-01"


def _invalid_value_warn(msgs: list[str]) -> bool:
    return any("Invalid value for prop `value` on <input>" in m for m in msgs)


@pytest.mark.skipif(not is_dev(), reason="invalid value DEV warnings")
def test_treats_initial_symbol_value_as_empty() -> None:
    c = Container()
    r = create_root(c)
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        r.render(create_element("input", {"type": "text", "value": Symbol(), "onChange": _noop}))
    assert _invalid_value_warn([str(w.message) for w in rec])
    assert _host(c).dom_input_value() == ""


@pytest.mark.skipif(not is_dev(), reason="invalid value DEV warnings")
def test_treats_updated_symbol_value_as_empty() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("input", {"type": "text", "value": "foo", "onChange": _noop}))
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        r.render(create_element("input", {"type": "text", "value": Symbol(), "onChange": _noop}))
    assert _invalid_value_warn([str(w.message) for w in rec])
    assert _host(c).dom_input_value() == ""


def test_treats_initial_symbol_defaultvalue_as_empty() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("input", {"type": "text", "defaultValue": Symbol()}))
    assert _host(c).dom_input_value() == ""


def test_treats_updated_symbol_defaultvalue_as_empty() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("input", {"type": "text", "defaultValue": "foo"}))
    r.render(create_element("input", {"type": "text", "defaultValue": Symbol()}))
    assert _host(c).dom_input_value() == "foo"


@pytest.mark.skipif(not is_dev(), reason="invalid value DEV warnings")
def test_treats_initial_function_value_as_empty() -> None:
    c = Container()
    r = create_root(c)
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        r.render(create_element("input", {"type": "text", "value": _noop, "onChange": _noop}))
    assert _invalid_value_warn([str(w.message) for w in rec])
    assert _host(c).dom_input_value() == ""


@pytest.mark.skipif(not is_dev(), reason="invalid value DEV warnings")
def test_treats_updated_function_value_as_empty() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("input", {"type": "text", "value": "foo", "onChange": _noop}))
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        r.render(create_element("input", {"type": "text", "value": _noop, "onChange": _noop}))
    assert _invalid_value_warn([str(w.message) for w in rec])
    assert _host(c).dom_input_value() == ""


def test_treats_initial_function_defaultvalue_as_empty() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("input", {"type": "text", "defaultValue": _noop}))
    assert _host(c).dom_input_value() == ""


def test_treats_updated_function_defaultvalue_as_empty() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("input", {"type": "text", "defaultValue": "foo"}))
    r.render(create_element("input", {"type": "text", "defaultValue": _noop}))
    assert _host(c).dom_input_value() == "foo"


def test_should_remove_previous_defaultvalue() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("input", {"type": "text", "defaultValue": "0"}))
    host = _host(c)
    assert host.dom_input_value() == "0"
    assert host.default_value == "0"
    r.render(create_element("input", {"type": "text"}))
    assert host.default_value == ""


@pytest.mark.skipif(not is_dev(), reason="null value DEV warning")
def test_should_warn_if_value_is_null() -> None:
    c = Container()
    r = create_root(c)
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        r.render(create_element("input", {"type": "text", "value": None}))
    assert any("`value` prop on `input` should not be null" in str(w.message) for w in rec)


def test_should_not_incur_unnecessary_dom_mutations() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("input", {"type": "text", "value": "a", "onChange": _noop}))
    c.ops.clear()
    r.render(create_element("input", {"type": "text", "value": "a", "onChange": _noop}))
    assert not any(op["op"] == "updateProps" for op in c.ops)


def test_should_not_incur_unnecessary_dom_mutations_for_numeric_type_conversion() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("input", {"type": "number", "value": 2, "onChange": _noop}))
    c.ops.clear()
    r.render(create_element("input", {"type": "number", "value": 2, "onChange": _noop}))
    assert not any(op["op"] == "updateProps" for op in c.ops)


def test_should_not_incur_unnecessary_dom_mutations_for_boolean_type_conversion() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("input", {"type": "checkbox", "checked": True, "onChange": _noop}))
    c.ops.clear()
    r.render(create_element("input", {"type": "checkbox", "checked": True, "onChange": _noop}))
    assert not any(op["op"] == "updateProps" for op in c.ops)


def test_does_change_the_number_2_to_2_0_with_no_change_handler() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("input", {"type": "number", "value": 2}))
    host = _host(c)
    assert host.dom_input_value() == "2"
    r.render(create_element("input", {"type": "number", "value": "2.0"}))
    assert host.dom_input_value() == "2.0"


def test_does_change_the_string_2_to_2_0_with_no_change_handler() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("input", {"type": "number", "value": "2"}))
    host = _host(c)
    r.render(create_element("input", {"type": "number", "value": "2.0"}))
    assert host.dom_input_value() == "2.0"


def test_updates_the_value_on_checkboxes_from_empty_to_0() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("input", {"type": "checkbox", "value": ""}))
    host = _host(c)
    r.render(create_element("input", {"type": "checkbox", "value": 0}))
    assert host.dom_input_value() == "0"


def test_updates_the_value_on_radio_buttons_from_empty_to_0() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("input", {"type": "radio", "value": ""}))
    host = _host(c)
    r.render(create_element("input", {"type": "radio", "value": 0}))
    assert host.dom_input_value() == "0"


def test_should_throw_for_text_inputs_if_value_is_temporal_like() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("input", {"type": "text", "value": "x", "onChange": _noop}))
    with pytest.raises(TypeError, match="prod message"):
        if is_dev():
            with warnings.catch_warnings(record=True):
                warnings.simplefilter("always")
                r.render(create_element("input", {"type": "text", "value": TemporalLike(), "onChange": _noop}))
        else:
            r.render(create_element("input", {"type": "text", "value": TemporalLike(), "onChange": _noop}))


@pytest.mark.skipif(not is_dev(), reason="controlled/uncontrolled DEV warnings")
def test_should_warn_if_controlled_input_switches_to_uncontrolled_with_defaultvalue() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("input", {"type": "text", "value": "x", "onChange": _noop}))
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        r.render(create_element("input", {"type": "text", "defaultValue": "y"}))
    assert any("changing a controlled input to be uncontrolled" in str(w.message) for w in rec)


@pytest.mark.skipif(not is_dev(), reason="controlled/uncontrolled DEV warnings")
def test_should_warn_if_uncontrolled_input_value_null_switches_to_controlled() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("input", {"type": "text"}))
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        r.render(create_element("input", {"type": "text", "value": "b", "onChange": _noop}))
    assert any("changing an uncontrolled input to be controlled" in str(w.message) for w in rec)
