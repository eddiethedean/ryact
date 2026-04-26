from __future__ import annotations

from ryact import create_element
from ryact_dom.dom import Container, ElementNode, TextNode
from ryact_dom.root import create_root


def test_multiple_keyed_children_text_updates_without_reparenting() -> None:
    # Upstream: ReactDOMComponent-test.js — "handles multiple child updates without interference"
    container = Container()
    root = create_root(container)

    root.render(
        create_element(
            "div",
            None,
            create_element("span", {"key": "a"}, "1"),
            create_element("span", {"key": "b"}, "2"),
        )
    )
    host = container.root.children[0]
    assert isinstance(host, ElementNode)
    assert len(host.children) == 2
    c0, c1 = host.children
    assert isinstance(c0, ElementNode) and isinstance(c1, ElementNode)
    assert isinstance(c0.children[0], TextNode)
    assert c0.children[0].text == "1"

    container.ops.clear()
    root.render(
        create_element(
            "div",
            None,
            create_element("span", {"key": "a"}, "x"),
            create_element("span", {"key": "b"}, "y"),
        )
    )
    assert container.root.children[0] is host
    assert host.children[0] is c0 and host.children[1] is c1
    assert isinstance(c0.children[0], TextNode)
    assert c0.children[0].text == "x"
    assert isinstance(c1.children[0], TextNode)
    assert c1.children[0].text == "y"
    assert any(op["op"] == "text" for op in container.ops)
    assert not any(op["op"] == "delete" for op in container.ops)
