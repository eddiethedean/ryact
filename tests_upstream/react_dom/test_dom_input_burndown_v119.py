"""ReactDOMInput-test.js parity: omit name, submit default, undefined value, 0 / 0.0 (v119)."""

from __future__ import annotations

from ryact import create_element
from ryact.element import UNDEFINED
from ryact_dom.dom import Container, ElementNode
from ryact_dom.root import create_root
from ryact_dom.server import render_to_string


def _noop(_e: object) -> None:
    return None


def test_should_not_render_name_if_not_supplied_022950aa() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("input", {"type": "text"}))
    host = c.root.children[0]
    assert isinstance(host, ElementNode)
    assert "name" not in host.props


def test_should_not_render_name_if_not_supplied_for_ssr_5610de80() -> None:
    html = render_to_string(create_element("input", {"type": "text"}))
    assert "name=" not in html.lower()


def test_should_not_set_value_for_submit_unnecessarily_79556118() -> None:
    html = render_to_string(create_element("input", {"type": "submit"}))
    assert "value=" not in html.lower()
    c = Container()
    r = create_root(c)
    r.render(create_element("input", {"type": "submit"}))
    host = c.root.children[0]
    assert isinstance(host, ElementNode)
    assert "value" not in host.props


def test_should_not_set_undefined_value_on_reset_cc22ecd0() -> None:
    html = render_to_string(create_element("input", {"type": "reset", "value": UNDEFINED}))
    assert "value=" not in html.lower()


def test_should_not_set_undefined_value_on_submit_1ca16103() -> None:
    html = render_to_string(create_element("input", {"type": "submit", "value": UNDEFINED}))
    assert "value=" not in html.lower()


def test_should_properly_control_value_of_number_0_bba231c3() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("input", {"type": "text", "value": 0, "onChange": _noop}))
    host = c.root.children[0]
    assert isinstance(host, ElementNode)
    assert host.dom_input_value() == "0"
    r.render(create_element("input", {"type": "text", "value": 0, "onChange": _noop}))
    assert host.dom_input_value() == "0"


def test_should_properly_control_0_0_for_number_input_7264cc82() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("input", {"type": "number", "value": 0.0, "onChange": _noop}))
    host = c.root.children[0]
    assert isinstance(host, ElementNode)
    assert host.dom_input_value() == "0"


def test_should_properly_control_0_0_for_text_input_b405fa99() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("input", {"type": "text", "value": 0.0, "onChange": _noop}))
    host = c.root.children[0]
    assert isinstance(host, ElementNode)
    assert host.dom_input_value() == "0"
