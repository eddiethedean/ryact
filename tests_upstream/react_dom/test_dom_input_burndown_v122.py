"""ReactDOMInput-test.js parity: SSR name/value/defaultValue, bigint, number transitions (v122)."""

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


def test_should_render_name_supplied_client_a4442279() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("input", {"type": "text", "name": "name"}))
    host = c.root.children[0]
    assert isinstance(host, ElementNode)
    assert host.props.get("name") == "name"


def test_should_render_name_supplied_ssr_e495ecd1() -> None:
    html = render_to_string(create_element("input", {"type": "text", "name": "name"}))
    assert 'name="name"' in html


def test_should_render_value_for_ssr_218a0721() -> None:
    html = render_to_string(
        create_element("input", {"type": "text", "value": "1", "onChange": _noop}),
    )
    assert 'value="1"' in html


def test_should_render_defaultvalue_for_ssr_32acfd53() -> None:
    html = render_to_string(create_element("input", {"type": "text", "defaultValue": "1"}))
    assert 'value="1"' in html
    assert "defaultvalue" not in html.lower()


def test_should_render_bigint_defaultvalue_for_ssr_d6480d82() -> None:
    html = render_to_string(create_element("input", {"type": "text", "defaultValue": 5}))
    assert 'value="5"' in html


def test_should_render_bigint_value_for_ssr_6dab5f72() -> None:
    html = render_to_string(create_element("input", {"type": "text", "value": 5, "onChange": _noop}))
    assert 'value="5"' in html


def test_number_input_transition_empty_to_string_zero_686edb34() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("input", {"type": "number", "value": "", "onChange": _noop}))
    r.render(create_element("input", {"type": "number", "value": "0", "onChange": _noop}))
    host = c.root.children[0]
    assert isinstance(host, ElementNode)
    assert host.dom_input_value() == "0"


def test_number_input_transition_empty_to_int_zero_e1134d6e() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("input", {"type": "number", "value": "", "onChange": _noop}))
    r.render(create_element("input", {"type": "number", "value": 0, "onChange": _noop}))
    host = c.root.children[0]
    assert isinstance(host, ElementNode)
    assert host.dom_input_value() == "0"


@pytest.mark.skipif(not is_dev(), reason="read-only controlled warning is DEV-only")
def test_distinguishes_precision_extra_zeroes_string_number_7dd230e7() -> None:
    c = Container()
    r = create_root(c)
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        r.render(create_element("input", {"type": "number", "value": "3.0000"}))
    assert any("without an `onChange` handler" in str(w.message) for w in rec)
    host = c.root.children[0]
    assert isinstance(host, ElementNode)
    assert host.dom_input_value() == "3.0000"
    r.render(create_element("input", {"type": "number", "value": "3"}))
    assert host.dom_input_value() == "3"
