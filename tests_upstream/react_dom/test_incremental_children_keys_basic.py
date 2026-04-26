from __future__ import annotations

from ryact import create_element
from ryact_dom.dom import Container, ElementNode
from ryact_dom.root import create_root


def _li(*, key: str, label: str) -> object:
    # Note: key is extracted by create_element from props.
    return create_element("li", {"key": key, "data": label})


def test_reorders_keyed_children_incrementally() -> None:
    # Upstream: ReactMultiChild-test.js
    # "should reorder bailed-out children"
    container = Container()
    root = create_root(container)

    root.render(create_element("ul", None, _li(key="a", label="A"), _li(key="b", label="B")))
    ul = container.root.children[0]
    assert isinstance(ul, ElementNode)
    a1 = ul.children[0]
    b1 = ul.children[1]
    assert isinstance(a1, ElementNode) and isinstance(b1, ElementNode)
    assert a1.props.get("data") == "A"
    assert b1.props.get("data") == "B"

    root.render(create_element("ul", None, _li(key="b", label="B"), _li(key="a", label="A")))
    ul2 = container.root.children[0]
    assert ul2 is ul
    assert ul2.children[0] is b1
    assert ul2.children[1] is a1
    assert any(op["op"] == "move" for op in container.ops)
