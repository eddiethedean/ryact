"""ReactDOMInput-test.js parity: numeric values, null value DEV warn, defaultValue object (v118)."""

from __future__ import annotations

import warnings

import pytest
from ryact import create_element
from ryact.dev import is_dev
from ryact_dom.dom import Container, ElementNode
from ryact_dom.root import create_root
from ryact_dom.server import render_to_string


def _noop(_e: object) -> None:
    return None


def test_should_display_value_of_number_0_295537a0() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("input", {"type": "text", "value": 0, "onChange": _noop}))
    host = c.root.children[0]
    assert isinstance(host, ElementNode)
    assert host.dom_input_value() == "0"


def test_should_display_value_of_bigint_5_cb4182b8() -> None:
    # ECMAScript BigInt maps to ``int`` in translated tests.
    c = Container()
    r = create_root(c)
    r.render(create_element("input", {"type": "text", "value": 5, "onChange": _noop}))
    host = c.root.children[0]
    assert isinstance(host, ElementNode)
    assert host.dom_input_value() == "5"


def test_performs_a_state_change_from_empty_to_0_b760b0b9() -> None:
    c = Container()
    r = create_root(c)
    r.render(
        create_element(
            "input",
            {"type": "number", "value": "", "readOnly": True, "onChange": _noop},
        )
    )
    host = c.root.children[0]
    assert isinstance(host, ElementNode)
    assert host.dom_input_value() == ""
    r.render(
        create_element(
            "input",
            {"type": "number", "value": 0, "readOnly": True, "onChange": _noop},
        )
    )
    assert host.dom_input_value() == "0"


def test_does_change_string_98_to_098_66082617() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("input", {"type": "number", "value": ".98", "onChange": _noop}))
    host = c.root.children[0]
    assert isinstance(host, ElementNode)
    assert host.dom_input_value() == ".98"
    r.render(create_element("input", {"type": "number", "value": "0.98", "onChange": _noop}))
    assert host.dom_input_value() == "0.98"


def test_should_not_set_null_value_on_reset_input_74082371() -> None:
    if is_dev():
        with warnings.catch_warnings(record=True) as rec:
            warnings.simplefilter("always")
            html = render_to_string(create_element("input", {"type": "reset", "value": None}))
        assert any("should not be null" in str(w.message) for w in rec)
    else:
        html = render_to_string(create_element("input", {"type": "reset", "value": None}))
    assert "value=" not in html.lower()
    c = Container()
    r = create_root(c)
    if is_dev():
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            r.render(create_element("input", {"type": "reset", "value": None}))
    else:
        r.render(create_element("input", {"type": "reset", "value": None}))
    host = c.root.children[0]
    assert isinstance(host, ElementNode)
    assert "value" not in host.props


def test_should_not_set_null_value_on_submit_input_c4c05b19() -> None:
    if is_dev():
        with warnings.catch_warnings(record=True) as rec:
            warnings.simplefilter("always")
            html = render_to_string(create_element("input", {"type": "submit", "value": None}))
        assert any("should not be null" in str(w.message) for w in rec)
    else:
        html = render_to_string(create_element("input", {"type": "submit", "value": None}))
    assert "value=" not in html.lower()


def test_should_display_foobar_for_defaultvalue_of_objtostring_e82e8cfb() -> None:
    class ObjToString:
        def __str__(self) -> str:
            return "foobar"

    html = render_to_string(create_element("input", {"type": "text", "defaultValue": ObjToString()}))
    assert 'value="foobar"' in html


@pytest.mark.skipif(not is_dev(), reason="null value warning is DEV-only")
def test_dev_warns_when_input_value_is_null() -> None:
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        render_to_string(create_element("input", {"type": "text", "value": None}))
    assert any("should not be null" in str(w.message) for w in rec)
