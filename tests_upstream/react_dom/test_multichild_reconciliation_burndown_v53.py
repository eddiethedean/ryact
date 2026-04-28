from __future__ import annotations

from ryact import create_element
from ryact_dom.dom import Container, ElementNode
from ryact_dom.root import create_root


def test_should_replace_children_with_different_keys() -> None:
    # Upstream: ReactMultiChild-test.js
    # "should replace children with different keys"
    container = Container()
    root = create_root(container)

    root.render(create_element("div", None, create_element("span", {"key": "a", "data": 1})))
    div = container.root.children[0]
    assert isinstance(div, ElementNode)
    a1 = div.children[0]
    assert isinstance(a1, ElementNode)

    root.render(create_element("div", None, create_element("span", {"key": "b", "data": 1})))
    div2 = container.root.children[0]
    assert div2 is div
    b1 = div2.children[0]
    assert isinstance(b1, ElementNode)
    assert b1 is not a1
    assert any(op["op"] == "delete" for op in container.ops)
    assert any(op["op"] == "insert" for op in container.ops)


def test_should_update_children_when_possible() -> None:
    # Upstream: ReactMultiChild-test.js
    # "should update children when possible"
    container = Container()
    root = create_root(container)

    root.render(create_element("div", None, create_element("span", {"key": "a", "data": 1})))
    div = container.root.children[0]
    assert isinstance(div, ElementNode)
    a1 = div.children[0]
    assert isinstance(a1, ElementNode)
    assert a1.props.get("data") == 1

    root.render(create_element("div", None, create_element("span", {"key": "a", "data": 2})))
    div2 = container.root.children[0]
    assert div2 is div
    a2 = div2.children[0]
    assert a2 is a1
    assert a2.props.get("data") == 2
    assert any(op["op"] == "updateProps" for op in container.ops)
    assert not any(op["op"] == "delete" for op in container.ops)


def test_should_replace_children_with_different_constructors() -> None:
    # Upstream: ReactMultiChild-test.js
    # "should replace children with different constructors"
    # We model "constructor" difference as a different host tag for the same key.
    container = Container()
    root = create_root(container)

    root.render(create_element("div", None, create_element("span", {"key": "a", "data": 1})))
    div = container.root.children[0]
    assert isinstance(div, ElementNode)
    a1 = div.children[0]
    assert isinstance(a1, ElementNode)
    assert a1.tag == "span"

    root.render(create_element("div", None, create_element("p", {"key": "a", "data": 1})))
    div2 = container.root.children[0]
    assert div2 is div
    a2 = div2.children[0]
    assert isinstance(a2, ElementNode)
    assert a2.tag == "p"
    assert a2 is not a1
    assert any(op["op"] == "delete" for op in container.ops)
    assert any(op["op"] == "insert" for op in container.ops)

