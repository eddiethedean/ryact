"""ReactDOMInput-test.js parity: checkbox/radio controlled warnings, Temporal, defaultValue (v131)."""

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


class TemporalLike:
    def valueOf(self) -> object:
        raise TypeError("prod message")

    def __str__(self) -> str:
        return "2020-01-01"


def _controlled_to_uncontrolled_warn(msgs: list[str]) -> bool:
    return any("changing a controlled input to be uncontrolled" in m for m in msgs)


def _uncontrolled_to_controlled_warn(msgs: list[str]) -> bool:
    return any("changing an uncontrolled input to be controlled" in m for m in msgs)


def _read_only_field_warn(msgs: list[str], *, prop: str) -> bool:
    if prop == "checked":
        return any(
            "provided a `checked` prop" in m and "without an `onChange` handler" in m and "readOnly" in m for m in msgs
        )
    return any(
        "provided a `value` prop" in m and "without an `onChange` handler" in m and "readOnly" in m for m in msgs
    )


@pytest.mark.skipif(not is_dev(), reason="controlled input DEV warnings")
def test_should_warn_if_controlled_checkbox_switches_to_uncontrolled_checked_is_undefined() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("input", {"type": "checkbox", "checked": True, "onChange": _noop}))
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        r.render(create_element("input", {"type": "checkbox"}))
    assert _controlled_to_uncontrolled_warn([str(w.message) for w in rec])


@pytest.mark.skipif(not is_dev(), reason="controlled input DEV warnings")
def test_should_warn_if_controlled_checkbox_switches_to_uncontrolled_checked_is_null() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("input", {"type": "checkbox", "checked": True, "onChange": _noop}))
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        r.render(create_element("input", {"type": "checkbox", "checked": None}))
    assert _controlled_to_uncontrolled_warn([str(w.message) for w in rec])


@pytest.mark.skipif(not is_dev(), reason="controlled input DEV warnings")
def test_should_warn_if_controlled_checkbox_switches_to_uncontrolled_with_defaultchecked() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("input", {"type": "checkbox", "checked": True, "onChange": _noop}))
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        r.render(create_element("input", {"type": "checkbox", "defaultChecked": True}))
    assert _controlled_to_uncontrolled_warn([str(w.message) for w in rec])


@pytest.mark.skipif(not is_dev(), reason="controlled input DEV warnings")
def test_should_warn_if_controlled_radio_switches_to_uncontrolled_checked_is_undefined() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("input", {"type": "radio", "checked": True, "onChange": _noop}))
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        r.render(create_element("input", {"type": "radio"}))
    assert _controlled_to_uncontrolled_warn([str(w.message) for w in rec])


@pytest.mark.skipif(not is_dev(), reason="controlled input DEV warnings")
def test_should_warn_if_controlled_radio_switches_to_uncontrolled_checked_is_null() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("input", {"type": "radio", "checked": True, "onChange": _noop}))
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        r.render(create_element("input", {"type": "radio", "checked": None}))
    assert _controlled_to_uncontrolled_warn([str(w.message) for w in rec])


@pytest.mark.skipif(not is_dev(), reason="controlled input DEV warnings")
def test_should_warn_if_controlled_radio_switches_to_uncontrolled_with_defaultchecked() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("input", {"type": "radio", "checked": True, "onChange": _noop}))
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        r.render(create_element("input", {"type": "radio", "defaultChecked": True}))
    assert _controlled_to_uncontrolled_warn([str(w.message) for w in rec])


@pytest.mark.skipif(not is_dev(), reason="controlled input DEV warnings")
def test_should_warn_if_uncontrolled_checkbox_checked_is_undefined_switches_to_controlled() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("input", {"type": "checkbox"}))
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        r.render(create_element("input", {"type": "checkbox", "checked": True, "onChange": _noop}))
    assert _uncontrolled_to_controlled_warn([str(w.message) for w in rec])


@pytest.mark.skipif(not is_dev(), reason="controlled input DEV warnings")
def test_should_warn_if_uncontrolled_checkbox_checked_is_null_switches_to_controlled() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("input", {"type": "checkbox", "checked": None}))
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        r.render(create_element("input", {"type": "checkbox", "checked": True, "onChange": _noop}))
    assert _uncontrolled_to_controlled_warn([str(w.message) for w in rec])


@pytest.mark.skipif(not is_dev(), reason="controlled input DEV warnings")
def test_should_warn_if_uncontrolled_radio_checked_is_undefined_switches_to_controlled() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("input", {"type": "radio"}))
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        r.render(create_element("input", {"type": "radio", "checked": True, "onChange": _noop}))
    assert _uncontrolled_to_controlled_warn([str(w.message) for w in rec])


@pytest.mark.skipif(not is_dev(), reason="controlled input DEV warnings")
def test_should_warn_if_uncontrolled_radio_checked_is_null_switches_to_controlled() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("input", {"type": "radio", "checked": None}))
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        r.render(create_element("input", {"type": "radio", "checked": True, "onChange": _noop}))
    assert _uncontrolled_to_controlled_warn([str(w.message) for w in rec])


@pytest.mark.skipif(not is_dev(), reason="controlled input DEV warnings")
def test_should_warn_if_radio_checked_false_changes_to_become_uncontrolled() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("input", {"type": "radio", "checked": False, "onChange": _noop}))
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        r.render(create_element("input", {"type": "radio"}))
    assert _controlled_to_uncontrolled_warn([str(w.message) for w in rec])


@pytest.mark.skipif(not is_dev(), reason="controlled input DEV warnings")
def test_should_warn_if_uncontrolled_input_value_is_undefined_switches_to_controlled() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("input", {"type": "text", "value": None}))
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        r.render(create_element("input", {"type": "text", "value": "b", "onChange": _noop}))
    assert _uncontrolled_to_controlled_warn([str(w.message) for w in rec])


@pytest.mark.skipif(not is_dev(), reason="controlled input DEV warnings")
def test_should_warn_with_checked_and_no_onchange_handler_with_readonly_specified() -> None:
    c = Container()
    r = create_root(c)
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        r.render(create_element("input", {"type": "checkbox", "checked": True}))
    assert _read_only_field_warn([str(w.message) for w in rec], prop="checked")


@pytest.mark.skipif(not is_dev(), reason="controlled input DEV warnings")
def test_should_warn_with_value_and_no_onchange_handler_and_readonly_specified() -> None:
    c = Container()
    r = create_root(c)
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        r.render(create_element("input", {"type": "text", "value": "x"}))
    assert _read_only_field_warn([str(w.message) for w in rec], prop="value")


def test_should_throw_for_text_inputs_if_defaultvalue_is_temporal_like() -> None:
    c = Container()
    r = create_root(c)
    with pytest.raises(TypeError, match="prod message"):
        if is_dev():
            with warnings.catch_warnings(record=True):
                warnings.simplefilter("always")
                r.render(create_element("input", {"type": "text", "defaultValue": TemporalLike()}))
        else:
            r.render(create_element("input", {"type": "text", "defaultValue": TemporalLike()}))


def test_should_throw_for_date_inputs_if_value_is_temporal_like() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("input", {"type": "date", "value": "2020-01-01", "onChange": _noop}))
    with pytest.raises(TypeError, match="prod message"):
        if is_dev():
            with warnings.catch_warnings(record=True):
                warnings.simplefilter("always")
                r.render(create_element("input", {"type": "date", "value": TemporalLike(), "onChange": _noop}))
        else:
            r.render(create_element("input", {"type": "date", "value": TemporalLike(), "onChange": _noop}))


def test_should_throw_for_date_inputs_if_defaultvalue_is_temporal_like() -> None:
    c = Container()
    r = create_root(c)
    with pytest.raises(TypeError, match="prod message"):
        if is_dev():
            with warnings.catch_warnings(record=True):
                warnings.simplefilter("always")
                r.render(create_element("input", {"type": "date", "defaultValue": TemporalLike()}))
        else:
            r.render(create_element("input", {"type": "date", "defaultValue": TemporalLike()}))


def test_only_assigns_defaultvalue_if_it_changes() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("input", {"type": "text", "defaultValue": "0"}))
    host = _host(c)
    assert host.default_value == "0"
    c.ops.clear()
    r.render(create_element("input", {"type": "text", "defaultValue": "0"}))
    assert not any(op["op"] == "updateProps" for op in c.ops)


@pytest.mark.skipif(not is_dev(), reason="controlled input DEV warnings")
def test_should_take_defaultvalue_when_changing_to_uncontrolled_input() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("input", {"type": "text", "value": "0", "onChange": _noop}))
    host = _host(c)
    assert host.dom_input_value() == "0"
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        r.render(create_element("input", {"type": "text", "defaultValue": "0"}))
    assert _controlled_to_uncontrolled_warn([str(w.message) for w in rec])
    assert host.dom_input_value() == "0"
