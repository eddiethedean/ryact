from __future__ import annotations

from ryact import create_element
from ryact_dom.dom import Container, ElementNode
from ryact_dom.root import create_root


def test_removing_normal_property_updates_host_incrementally() -> None:
    # Upstream: DOMPropertyOperations-test.js — "should remove attributes for normal properties"
    container = Container()
    root = create_root(container)

    root.render(create_element("div", {"title": "hello"}))
    host = container.root.children[0]
    assert isinstance(host, ElementNode)
    assert host.props.get("title") == "hello"

    root.render(create_element("div", {}))
    host2 = container.root.children[0]
    assert host2 is host
    assert "title" not in host2.props
    assert any(op["op"] == "updateProps" for op in container.ops)
