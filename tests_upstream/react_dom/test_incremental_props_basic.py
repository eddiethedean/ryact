from __future__ import annotations

from ryact import create_element
from ryact_dom.dom import Container, ElementNode
from ryact_dom.root import create_root


def test_switching_between_null_and_undefined_updates_a_property_incrementally() -> None:
    # Upstream: DOMPropertyOperations-test.js
    # "switching between null and undefined should update a property"
    container = Container()
    root = create_root(container)

    root.render(create_element("div", {"id": "x"}))
    assert isinstance(container.root.children[0], ElementNode)
    el1 = container.root.children[0]
    assert el1.props.get("id") == "x"

    root.render(create_element("div", {}))
    el2 = container.root.children[0]
    assert el2 is el1
    assert "id" not in el2.props
    assert any(op["op"] == "updateProps" for op in container.ops)
