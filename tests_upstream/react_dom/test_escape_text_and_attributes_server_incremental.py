from __future__ import annotations

from ryact import create_element
from ryact_dom.dom import Container, ElementNode, TextNode
from ryact_dom.root import create_root
from ryact_dom.server import render_to_string


def test_escapes_text_and_attribute_values_in_server_markup() -> None:
    # Upstream: ReactDOMComponent-test.js — escape text and attribute values in markup.
    nasty = 'say "hi" & <tag>'
    html = render_to_string(create_element("div", {"title": nasty}, nasty))
    assert "&quot;" in html or "&#34;" in html
    assert "&amp;" in html
    assert "&lt;" in html and "&gt;" in html


def test_preserves_raw_text_in_host_while_server_string_escapes() -> None:
    raw = "1<b>2</b>3&"
    container = Container()
    root = create_root(container)
    root.render(create_element("span", None, raw))
    host = container.root.children[0]
    assert isinstance(host, ElementNode)
    assert len(host.children) == 1
    t = host.children[0]
    assert isinstance(t, TextNode)
    assert t.text == raw
