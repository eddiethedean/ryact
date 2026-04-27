from __future__ import annotations

from ryact import create_element
from ryact_dom.dom import Container, ElementNode
from ryact_dom.root import create_root
from ryact_dom.server import render_to_string


def test_input_keeps_empty_value_attribute_when_stringified() -> None:
    # Upstream: DOMPropertyOperations-test.js
    # "should not remove empty attributes for special input properties"
    html = render_to_string(create_element("input", {"type": "text", "value": ""}))
    assert "value" in html.lower()


def test_non_input_meter_includes_value_attribute() -> None:
    # Upstream: DOMPropertyOperations-test.js
    # "should always assign the value attribute for non-inputs"
    html = render_to_string(create_element("meter", {"value": 0.4, "min": 0, "max": 1}))
    assert "value" in html.lower() and "0.4" in html

    container = Container()
    root = create_root(container)
    root.render(create_element("meter", {"value": 0.2, "min": 0, "max": 1}))
    host = container.root.children[0]
    assert isinstance(host, ElementNode)
    assert host.props.get("value") == 0.2
