from __future__ import annotations

import pytest

from ryact import create_element
from ryact_dom.dom import Container, ElementNode
from ryact_dom.root import create_root


def _first_element(node: ElementNode) -> ElementNode:
    for c in node.children:
        if isinstance(c, ElementNode):
            return c
    raise AssertionError("Expected an ElementNode child")


def test_should_not_prevent_null_listeners_at_dispatch() -> None:
    # Upstream: InvalidEventListeners-test.js
    c = Container()
    root = create_root(c)
    root.render(create_element("button", {"onClick": None}))
    btn = _first_element(c.root)
    btn.dispatch_event("click")


def test_should_prevent_non_function_listeners_at_dispatch() -> None:
    # Upstream: InvalidEventListeners-test.js
    c = Container()
    root = create_root(c)
    root.render(create_element("button", {"onClick": 123}))
    btn = _first_element(c.root)
    with pytest.raises(TypeError, match="onClick"):
        btn.dispatch_event("click")

