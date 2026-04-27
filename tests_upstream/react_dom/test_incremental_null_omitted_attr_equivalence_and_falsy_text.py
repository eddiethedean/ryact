from __future__ import annotations

from ryact import create_element
from ryact_dom.dom import Container, ElementNode
from ryact_dom.root import create_root
from ryact_dom.server import render_to_string


def test_should_not_update_when_switching_between_null_and_omitted_attribute() -> None:
    # Upstream: ReactDOMComponent-test.js — updateDOM
    # "should not update when switching between null/undefined"
    container = Container()
    root = create_root(container)
    root.render(create_element("div", {"id": "host", "title": None}))
    host = container.root.children[0]
    assert isinstance(host, ElementNode)
    assert "title" not in host.props

    container.ops.clear()
    root.render(create_element("div", {"id": "host"}))
    host2 = container.root.children[0]
    assert host2 is host
    assert not any(op["op"] == "updateProps" for op in container.ops)


def test_should_render_null_child_empty_and_zero_as_text() -> None:
    # Upstream: ReactDOMComponent-test.js — updateDOM
    # "should render null and undefined as empty but print other falsy values"
    assert render_to_string(create_element("div", None, None)) == "<div></div>"
    assert render_to_string(create_element("div", None, 0)) == "<div>0</div>"
