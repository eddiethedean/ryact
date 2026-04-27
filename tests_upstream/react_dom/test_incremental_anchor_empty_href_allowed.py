from __future__ import annotations

from ryact import create_element
from ryact_dom.dom import Container, ElementNode
from ryact_dom.root import create_root
from ryact_dom.server import render_to_string


def test_anchor_preserves_empty_href_in_markup_and_host_props() -> None:
    # Upstream: ReactDOMComponent-test.js — "should allow an empty href attribute on anchors"
    html = render_to_string(create_element("a", {"href": "", "text": "x"}))
    assert "href" in html.lower()

    container = Container()
    root = create_root(container)
    root.render(create_element("a", {"href": "https://example.com", "text": "home"}))
    host = container.root.children[0]
    assert isinstance(host, ElementNode)
    assert host.props.get("href") == "https://example.com"

    root.render(create_element("a", {"href": "", "text": "empty"}))
    host2 = container.root.children[0]
    assert host2 is host
    assert host2.props.get("href") == ""
