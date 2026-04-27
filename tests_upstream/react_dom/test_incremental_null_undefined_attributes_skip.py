from __future__ import annotations

from ryact import create_element
from ryact_dom.dom import Container, ElementNode
from ryact_dom.root import create_root
from ryact_dom.server import render_to_string


def test_nullish_scalar_props_do_not_emit_attributes() -> None:
    # Upstream: ReactDOMComponent-test.js — "should not set null/undefined attributes"
    html = render_to_string(create_element("div", {"id": "x", "title": None, "lang": None}))
    assert 'id="x"' in html
    assert "title=" not in html
    assert "lang=" not in html

    container = Container()
    root = create_root(container)
    root.render(create_element("div", {"id": "host", "data_tip": "1"}))
    host = container.root.children[0]
    assert isinstance(host, ElementNode)
    assert host.props.get("data_tip") == "1"

    root.render(create_element("div", {"id": "host", "data_tip": None}))
    host2 = container.root.children[0]
    assert host2 is host
    assert "data_tip" not in host2.props
    assert any(op["op"] == "updateProps" for op in container.ops)
