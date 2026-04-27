from __future__ import annotations

from ryact import create_element
from ryact_dom.dom import Container, ElementNode
from ryact_dom.root import create_root
from ryact_dom.server import render_to_string


def test_falsey_boolean_props_omit_attribute_server_and_incremental() -> None:
    # Upstream: DOMPropertyOperations-test.js
    # "should remove for falsey boolean properties"
    for val in (0, ""):
        html = render_to_string(create_element("input", {"type": "checkbox", "checked": val}))
        assert "checked" not in html.lower()

    container = Container()
    root = create_root(container)
    root.render(create_element("button", {"type": "button", "disabled": True}))
    host = container.root.children[0]
    assert isinstance(host, ElementNode)
    assert host.props.get("disabled") is True

    root.render(create_element("button", {"type": "button", "disabled": 0}))
    host2 = container.root.children[0]
    assert host2 is host
    assert "disabled" not in host2.props
    assert any(op["op"] == "updateProps" for op in container.ops)
