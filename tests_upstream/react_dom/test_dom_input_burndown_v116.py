"""ReactDOMInput-test.js parity: ``value`` coercion and checkbox/radio default ``on`` (v116)."""

from __future__ import annotations

from ryact import create_element
from ryact_dom.dom import Container, ElementNode
from ryact_dom.root import create_root
from ryact_dom.server import render_to_string


def _noop(_e: object) -> None:
    return None


def test_should_allow_setting_value_to_false_d8c98d06() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("input", {"type": "text", "value": "yolo", "onChange": _noop}))
    host = c.root.children[0]
    assert isinstance(host, ElementNode)
    assert host.props.get("value") == "yolo"
    r.render(create_element("input", {"type": "text", "value": False, "onChange": _noop}))
    assert host.dom_input_value() == "false"
    assert host.props.get("value") == "false"


def test_should_allow_setting_value_to_true_7ddcaef7() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("input", {"type": "text", "value": "yolo", "onChange": _noop}))
    host = c.root.children[0]
    assert isinstance(host, ElementNode)
    r.render(create_element("input", {"type": "text", "value": True, "onChange": _noop}))
    assert host.dom_input_value() == "true"


def test_should_allow_setting_value_to_obj_to_string_fde3d903() -> None:
    class ObjToString:
        def __str__(self) -> str:
            return "foobar"

    c = Container()
    r = create_root(c)
    r.render(create_element("input", {"type": "text", "value": "foo", "onChange": _noop}))
    host = c.root.children[0]
    assert isinstance(host, ElementNode)
    r.render(create_element("input", {"type": "text", "value": ObjToString(), "onChange": _noop}))
    assert host.dom_input_value() == "foobar"


def test_checkbox_checked_does_not_serialize_value_on_attr_ffa30c6d() -> None:
    html = render_to_string(create_element("input", {"type": "checkbox", "checked": True}))
    assert "value=" not in html.lower()
    c = Container()
    r = create_root(c)
    r.render(create_element("input", {"type": "checkbox", "checked": True}))
    host = c.root.children[0]
    assert isinstance(host, ElementNode)
    assert "value" not in host.props
    assert host.dom_input_value() == "on"


def test_radio_checked_does_not_serialize_value_on_attr_f5c8dde2() -> None:
    html = render_to_string(create_element("input", {"type": "radio", "checked": True}))
    assert "value=" not in html.lower()
    c = Container()
    r = create_root(c)
    r.render(create_element("input", {"type": "radio", "checked": True}))
    host = c.root.children[0]
    assert isinstance(host, ElementNode)
    assert "value" not in host.props
    assert host.dom_input_value() == "on"


def test_ssr_input_value_false_emits_string_false_attribute() -> None:
    html = render_to_string(create_element("input", {"type": "text", "value": False}))
    assert 'value="false"' in html


def test_textarea_default_value_bool_stringifies() -> None:
    html = render_to_string(create_element("textarea", {"defaultValue": True}))
    assert "true" in html.lower()
