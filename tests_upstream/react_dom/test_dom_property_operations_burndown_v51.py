# Translated: DOMPropertyOperations — custom element non-event callables as properties
from __future__ import annotations

from ryact import create_element
from ryact_dom.dom import Container, ElementNode
from ryact_dom.root import create_root
from ryact_dom.server import render_to_string


def my_fn() -> str:
    return "ok"


def test_custom_element_host_keeps_function_property() -> None:
    c = create_root(Container())
    c.render(create_element("my-custom-element", {"foo": my_fn}))

    host = c.container.root.children[0]
    assert isinstance(host, ElementNode)
    assert host.props.get("foo") is my_fn
    # No HTML attribute for ad-hoc function property (parity with attribute omission).
    html = render_to_string(create_element("my-custom-element", {"foo": my_fn}))
    assert "my-custom-element" in html
    assert "foo" not in html  # not stringified into markup
