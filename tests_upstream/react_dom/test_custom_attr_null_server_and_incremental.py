from __future__ import annotations

from ryact import create_element
from ryact_dom.dom import Container, ElementNode
from ryact_dom.root import create_root
from ryact_dom.server import render_to_string


def test_custom_data_attr_null_removes_server_and_incremental() -> None:
    # Upstream: DOMPropertyOperations-test.js — "should remove when setting custom attr to null"
    html0 = render_to_string(create_element("div", {"data_x": "1"}, "z"))
    assert "data-x" in html0

    html1 = render_to_string(create_element("div", {"data_x": None}, "z"))
    assert "data-x" not in html1

    container = Container()
    root = create_root(container)
    root.render(create_element("div", {"data_foo": "keep"}))
    host = container.root.children[0]
    assert isinstance(host, ElementNode)
    assert host.props.get("data_foo") == "keep"

    root.render(create_element("div", {"data_foo": None}))
    host2 = container.root.children[0]
    assert host2 is host
    assert "data_foo" not in host2.props
    assert any(op["op"] == "updateProps" for op in container.ops)
