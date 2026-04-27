from __future__ import annotations

from ryact import create_element
from ryact_dom.dom import Container, ElementNode
from ryact_dom.root import create_root
from ryact_dom.server import render_to_string


def test_object_custom_attribute_stringified_server_and_incremental() -> None:
    # Upstream: ReactDOMComponent — "will assign an object custom attributes"
    payload: dict[str, bool] = {"nested": True}
    html = render_to_string(create_element("div", {"whatever": payload}))
    assert "whatever=" in html.lower()

    container = Container()
    root = create_root(container)
    root.render(create_element("div", {"whatever": payload}))
    host = container.root.children[0]
    assert isinstance(host, ElementNode)
    assert host.props.get("whatever") == str(payload)


def test_function_custom_attribute_not_assigned_server_or_incremental() -> None:
    # Upstream: ReactDOMComponent — "will not assign a function custom attributes"
    def _fn() -> None:
        return None

    html = render_to_string(create_element("div", {"whatever": _fn}))
    assert "whatever" not in html.lower()

    container = Container()
    root = create_root(container)
    root.render(create_element("div", {"whatever": _fn}))
    host = container.root.children[0]
    assert isinstance(host, ElementNode)
    assert "whatever" not in host.props
