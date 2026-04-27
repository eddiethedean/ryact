from __future__ import annotations

from ryact import create_element
from ryact_dom.dom import Container, ElementNode
from ryact_dom.root import create_root
from ryact_dom.server import render_to_string


def test_custom_data_attribute_string_server_and_incremental() -> None:
    # Upstream: ReactDOMComponent-test.js — Custom attributes
    # "allows assignment of custom attributes with string values"
    html = render_to_string(create_element("div", {"data_foo": "hello"}))
    assert 'data-foo="hello"' in html

    container = Container()
    root = create_root(container)
    root.render(create_element("div", {"data_bar": "a"}))
    host = container.root.children[0]
    assert isinstance(host, ElementNode)
    assert host.props.get("data_bar") == "a"

    root.render(create_element("div", {"data_bar": "b"}))
    host2 = container.root.children[0]
    assert host2 is host
    assert host2.props.get("data_bar") == "b"
    assert any(op["op"] == "updateProps" for op in container.ops)


def test_cased_custom_attribute_names_preserved_server() -> None:
    # Upstream: ReactDOMComponent-test.js — Custom attributes
    # "allows cased custom attributes"
    html = render_to_string(create_element("div", {"myCustomAttr": "x"}))
    assert "myCustomAttr" in html
    assert 'myCustomAttr="x"' in html
