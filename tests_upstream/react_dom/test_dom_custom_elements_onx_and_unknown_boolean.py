from __future__ import annotations

from ryact import create_element
from ryact_dom.dom import Container, ElementNode
from ryact_dom.root import create_root
from ryact_dom.server import render_to_string

_CUSTOM = "some-custom-element"


def test_custom_element_does_not_strip_unknown_boolean_attributes() -> None:
    # Upstream: ReactDOMComponent-test.js — Custom elements
    # "does not strip unknown boolean attributes"
    html = render_to_string(create_element(_CUSTOM, {"foo": True}))
    assert 'foo=""' in html

    container = Container()
    root = create_root(container)
    root.render(create_element(_CUSTOM, {"foo": True}))
    host = container.root.children[0]
    assert isinstance(host, ElementNode)
    assert host.tag == _CUSTOM
    assert host.props.get("foo") == ""

    root.render(create_element(_CUSTOM, {"foo": False}))
    assert host.props.get("foo") is None

    root.render(create_element(_CUSTOM))
    assert "foo" not in host.props

    root.render(create_element(_CUSTOM, {"foo": True}))
    assert "foo" in host.props


def test_custom_element_does_not_strip_string_on_prefixed_attributes() -> None:
    # Upstream: ReactDOMComponent-test.js — Custom elements
    # "does not strip the on* attributes"
    html = render_to_string(create_element(_CUSTOM, {"onx": "bar"}))
    assert 'onx="bar"' in html

    container = Container()
    root = create_root(container)
    root.render(create_element(_CUSTOM, {"onx": "bar"}))
    host = container.root.children[0]
    assert isinstance(host, ElementNode)
    assert host.props.get("onx") == "bar"

    root.render(create_element(_CUSTOM, {"onx": "buzz"}))
    assert host.props.get("onx") == "buzz"

    root.render(create_element(_CUSTOM))
    assert "onx" not in host.props

    root.render(create_element(_CUSTOM, {"onx": "bar"}))
    assert host.props.get("onx") == "bar"
