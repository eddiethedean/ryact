from __future__ import annotations

from ryact import create_element
from ryact_dom.dom import Container, ElementNode
from ryact_dom.root import create_root


def test_classname_null_clears_to_empty_string_on_host() -> None:
    # Upstream: DOMPropertyOperations-test.js — className clears to "" not omitted.
    container = Container()
    root = create_root(container)

    root.render(create_element("div", {"className": "active"}))
    host = container.root.children[0]
    assert isinstance(host, ElementNode)
    assert host.props.get("class") == "active"

    root.render(create_element("div", {"className": None}))
    host2 = container.root.children[0]
    assert host2 is host
    assert host2.props.get("class") == ""
    assert any(op["op"] == "updateProps" for op in container.ops)
