from __future__ import annotations

from ryact import create_element
from ryact_dom.dom import Container, ElementNode
from ryact_dom.root import create_root
from ryact_dom.server import render_to_string


def test_custom_data_attribute_removed_on_update() -> None:
    # Upstream: ReactDOMComponent-test.js — Custom attributes — "removes custom attributes"
    html1 = render_to_string(create_element("div", {"data_x": "30"}))
    assert "data-x" in html1.lower() and "30" in html1
    html2 = render_to_string(create_element("div", {}))
    assert "data-x" not in html2.lower()

    container = Container()
    root = create_root(container)
    root.render(create_element("div", {"data_y": "hello"}))
    host = container.root.children[0]
    assert isinstance(host, ElementNode)
    assert host.props.get("data_y") == "hello"

    root.render(create_element("div", {}))
    host2 = container.root.children[0]
    assert host2 is host
    assert "data_y" not in host2.props


def test_custom_attribute_dropped_when_value_becomes_invalid_callable() -> None:
    # Upstream: ReactDOMComponent-test.js — "removes a property when it becomes invalid"
    def _bad() -> str:
        return "no"

    html1 = render_to_string(create_element("div", {"whatever": "30"}))
    assert "whatever" in html1.lower()
    html2 = render_to_string(create_element("div", {"whatever": _bad}))
    assert "whatever" not in html2.lower()

    container = Container()
    root = create_root(container)
    root.render(create_element("div", {"whatever": "30"}))
    host = container.root.children[0]
    assert isinstance(host, ElementNode)
    assert host.props.get("whatever") == "30"

    root.render(create_element("div", {"whatever": _bad}))
    host2 = container.root.children[0]
    assert host2 is host
    assert "whatever" not in host2.props
