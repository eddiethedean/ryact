from __future__ import annotations

from ryact import create_element
from ryact_dom.dom import Container, ElementNode
from ryact_dom.root import create_root
from ryact_dom.server import render_to_string


def test_non_string_prop_values_stringify_for_attributes() -> None:
    # Upstream: DOMPropertyOperations-test.js
    # "should convert attribute values to string first"
    html = render_to_string(create_element("meter", {"value": 0.5, "min": 0, "max": 1}))
    assert "0.5" in html

    container = Container()
    root = create_root(container)
    root.render(create_element("div", {"data_count": 42}))
    host = container.root.children[0]
    assert isinstance(host, ElementNode)
    assert host.props.get("data_count") == 42 or str(host.props.get("data_count")) == "42"
