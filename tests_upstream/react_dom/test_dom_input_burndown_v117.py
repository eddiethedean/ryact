"""ReactDOMInput-test.js parity: defaultValue→value, prop order, value before type (v117)."""

from __future__ import annotations

from ryact import create_element
from ryact_dom.dom import Container, ElementNode
from ryact_dom.html_props import normalize_host_prop_dict
from ryact_dom.mount_validation import prepare_host_mount_props
from ryact_dom.root import create_root
from ryact_dom.server import render_to_string


def _noop(_e: object) -> None:
    return None


def test_sets_type_step_min_max_before_value_always_ecd850c3() -> None:
    html = render_to_string(
        create_element(
            "input",
            {
                "value": "0",
                "onChange": _noop,
                "type": "range",
                "min": "0",
                "max": "100",
                "step": "1",
            },
        )
    )
    i_min = html.index("min")
    i_max = html.index("max")
    i_step = html.index("step")
    i_type = html.index("type")
    i_val = html.index("value")
    assert i_min < i_max < i_step < i_type < i_val


def test_sets_value_properly_with_type_coming_later_in_props_691e50ad() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("input", {"value": "hi", "type": "radio", "onChange": _noop}))
    host = c.root.children[0]
    assert isinstance(host, ElementNode)
    assert host.dom_input_value() == "hi"
    keys = list(host.props.keys())
    assert keys.index("type") < keys.index("value")


def test_should_display_defaultvalue_of_number_0_5e6708a9() -> None:
    html = render_to_string(create_element("input", {"type": "text", "defaultValue": 0}))
    assert 'value="0"' in html
    assert "defaultvalue" not in html.lower()
    c = Container()
    r = create_root(c)
    r.render(create_element("input", {"type": "text", "defaultValue": 0}))
    host = c.root.children[0]
    assert isinstance(host, ElementNode)
    assert host.props.get("value") == 0
    assert host.dom_input_value() == "0"


def test_should_display_false_for_defaultvalue_of_false_806610f0() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("input", {"type": "text", "defaultValue": False}))
    host = c.root.children[0]
    assert isinstance(host, ElementNode)
    assert host.dom_input_value() == "false"


def test_should_display_true_for_defaultvalue_of_true_b03af78d() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("input", {"type": "text", "defaultValue": True}))
    host = c.root.children[0]
    assert isinstance(host, ElementNode)
    assert host.dom_input_value() == "true"


def test_normalize_input_strips_defaultvalue_when_value_present() -> None:
    n = normalize_host_prop_dict(
        prepare_host_mount_props({"type": "text", "value": "x", "defaultValue": "y"}, tag="input"),
        tag="input",
    )
    assert n.get("value") == "x"
    assert "defaultValue" not in n and "default_value" not in n
