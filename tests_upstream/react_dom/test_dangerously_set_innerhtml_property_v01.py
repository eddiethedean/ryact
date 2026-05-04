from __future__ import annotations

from ryact import create_element
from ryact_dom.dom import Container, ElementNode
from ryact_dom.root import create_root


def _first_element(node: ElementNode) -> ElementNode:
    for c in node.children:
        if isinstance(c, ElementNode):
            return c
    raise AssertionError("Expected an ElementNode child")


def test_sets_innerhtml_on_it() -> None:
    # Upstream: dangerouslySetInnerHTML-test.js
    c = Container()
    root = create_root(c)
    root.render(create_element("div", {"dangerouslySetInnerHTML": {"__html": "<span>Hi</span>"}}))
    div = _first_element(c.root)
    assert div.innerHTML == "<span>Hi</span>"
