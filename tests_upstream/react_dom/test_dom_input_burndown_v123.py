"""ReactDOMInput-test.js parity: text value transitions, type switch, reset/submit value (v123)."""

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


def test_transition_text_empty_to_zero_a9f9d99b() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("input", {"type": "text", "value": "", "onChange": _noop}))
    r.render(create_element("input", {"type": "text", "value": 0, "onChange": _noop}))
    host = c.root.children[0]
    assert isinstance(host, ElementNode)
    assert host.dom_input_value() == "0"


def test_transition_text_zero_to_empty_950bf086() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("input", {"type": "text", "value": 0, "onChange": _noop}))
    r.render(create_element("input", {"type": "text", "value": "", "onChange": _noop}))
    host = c.root.children[0]
    assert isinstance(host, ElementNode)
    assert host.dom_input_value() == ""


def test_transition_text_zero_to_string_zero_point_zero_48193ce2() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("input", {"type": "text", "value": 0, "onChange": _noop}))
    r.render(create_element("input", {"type": "text", "value": "0.0", "onChange": _noop}))
    host = c.root.children[0]
    assert isinstance(host, ElementNode)
    assert host.dom_input_value() == "0.0"


@pytest.mark.skipif(not is_dev(), reason="invalid value warnings are DEV-only")
def test_no_invalid_value_warning_when_switching_types_8a3184cd() -> None:
    c = Container()
    r = create_root(c)
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        r.render(create_element("input", {"type": "number", "value": 1000, "onChange": _noop}))
        r.render(create_element("input", {"type": "text", "value": "Test", "onChange": _noop}))
    msgs = [str(w.message) for w in rec]
    assert not any("Invalid value for prop `value`" in m for m in msgs)
    host = c.root.children[0]
    assert isinstance(host, ElementNode)
    assert host.dom_input_value() == "Test"


def test_set_value_on_reset_input_b7eeb289() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("input", {"type": "reset", "value": "banana"}))
    host = c.root.children[0]
    assert isinstance(host, ElementNode)
    assert host.props.get("value") == "banana"
    html = render_to_string(create_element("input", {"type": "reset", "value": "banana"}))
    assert 'type="reset"' in html and 'value="banana"' in html


def test_set_empty_string_value_on_reset_input_cf60bb3d() -> None:
    html = render_to_string(create_element("input", {"type": "reset", "value": ""}))
    assert 'value=""' in html


def test_set_empty_string_value_on_submit_input_918c5d41() -> None:
    html = render_to_string(create_element("input", {"type": "submit", "value": ""}))
    assert 'value=""' in html
