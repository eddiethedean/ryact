from __future__ import annotations

from ryact import create_element
from ryact_dom.dom import Container, ElementNode
from ryact_dom.root import create_root
from ryact_dom.server import render_to_string


def test_empty_href_not_serialized_server_or_host_props() -> None:
    # Upstream: ReactDOMComponent-test.js — "should not add an empty href attribute"
    # Use <link>: empty href is still omitted (anchors are special-cased separately).
    html = render_to_string(create_element("link", {"href": "", "rel": "stylesheet"}))
    assert "href" not in html.lower()

    container = Container()
    root = create_root(container)
    root.render(
        create_element(
            "link",
            {"href": "https://example.com/style.css", "rel": "stylesheet"},
        ),
    )
    host = container.root.children[0]
    assert isinstance(host, ElementNode)
    assert host.props.get("href") == "https://example.com/style.css"

    root.render(create_element("link", {"href": "", "rel": "stylesheet"}))
    host2 = container.root.children[0]
    assert host2 is host
    assert "href" not in host2.props
