from __future__ import annotations

from ryact import create_element
from ryact_dom.dom import Container, ElementNode, TextNode
from ryact_dom.root import create_root


def test_resetting_direct_text_child_removes_text_node_incrementally() -> None:
    # Upstream: ReactDOMComponent-test.js
    # "should reset innerHTML when switching from a direct text child to an empty child"
    container = Container()
    root = create_root(container)

    root.render(create_element("div", None, "hello"))
    host = container.root.children[0]
    assert isinstance(host, ElementNode)
    t = host.children[0]
    assert isinstance(t, TextNode)
    assert t.text == "hello"

    root.render(create_element("div", {}))
    host2 = container.root.children[0]
    assert host2 is host
    assert host2.children == []
    assert any(op["op"] == "delete" for op in container.ops)
