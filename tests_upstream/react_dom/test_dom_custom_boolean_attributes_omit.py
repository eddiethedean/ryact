from __future__ import annotations

from ryact import create_element
from ryact_dom.dom import Container, ElementNode
from ryact_dom.root import create_root
from ryact_dom.server import render_to_string


def test_explicit_boolean_custom_attribute_not_assigned_server_or_client() -> None:
    # Upstream: ReactDOMComponent-test.js — Custom attributes
    # "does not assign a boolean custom attributes as a string"
    html = render_to_string(create_element("div", {"whatever": True}))
    assert "whatever" not in html.lower()

    container = Container()
    root = create_root(container)
    root.render(create_element("div", {"whatever": True}))
    host = container.root.children[0]
    assert isinstance(host, ElementNode)
    assert "whatever" not in host.props


def test_implicit_style_boolean_custom_attribute_not_assigned_server_or_client() -> None:
    # Upstream: ReactDOMComponent-test.js — Custom attributes
    # "does not assign an implicit boolean custom attributes" (JSX boolean shorthand → true)
    html = render_to_string(create_element("div", {"myFlag": True}))
    assert "myflag" not in html.lower()

    container = Container()
    root = create_root(container)
    root.render(create_element("div", {"myFlag": True}))
    host = container.root.children[0]
    assert isinstance(host, ElementNode)
    assert "myFlag" not in host.props
