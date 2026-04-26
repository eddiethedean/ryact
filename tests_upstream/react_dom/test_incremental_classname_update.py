from __future__ import annotations

from ryact import create_element
from ryact_dom.dom import Container, ElementNode
from ryact_dom.root import create_root


def test_classname_update_applies_incrementally() -> None:
    # Upstream: ReactDOMComponent-test.js — "should handle className"
    container = Container()
    root = create_root(container)

    root.render(create_element("div", {"className": "a"}))
    host = container.root.children[0]
    assert isinstance(host, ElementNode)
    assert host.props.get("class") == "a"

    root.render(create_element("div", {"className": "b"}))
    host2 = container.root.children[0]
    assert host2 is host
    assert host2.props.get("class") == "b"
    assert any(op["op"] == "updateProps" for op in container.ops)
