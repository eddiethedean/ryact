from __future__ import annotations

from ryact import create_element
from ryact_dom.dom import Container, ElementNode
from ryact_dom.root import create_root
from ryact_dom.server import render_to_string


def test_empty_src_not_serialized_server_or_host_props() -> None:
    # Upstream: ReactDOMComponent-test.js — "should not add an empty src attribute"
    html = render_to_string(create_element("img", {"src": "", "alt": "x"}))
    assert "src" not in html.lower()

    container = Container()
    root = create_root(container)
    root.render(create_element("img", {"src": "https://example.com/x.png", "alt": "a"}))
    host = container.root.children[0]
    assert isinstance(host, ElementNode)
    assert host.props.get("src") == "https://example.com/x.png"

    root.render(create_element("img", {"src": "", "alt": "b"}))
    host2 = container.root.children[0]
    assert host2 is host
    assert "src" not in host2.props
