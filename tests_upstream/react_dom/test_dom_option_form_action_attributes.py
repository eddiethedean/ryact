from __future__ import annotations

from ryact import create_element
from ryact_dom.dom import Container, ElementNode
from ryact_dom.root import create_root
from ryact_dom.server import render_to_string


def test_option_preserves_empty_value_attribute() -> None:
    # Upstream: DOMPropertyOperations-test.js
    # "should not remove empty attributes for special option properties"
    html = render_to_string(
        create_element(
            "select",
            None,
            create_element("option", {"value": "", "text": "empty"}),
        ),
    )
    assert "option" in html.lower()
    assert "value" in html.lower()


def test_form_allows_empty_action_attribute() -> None:
    # Upstream: ReactDOMComponent-test.js — "should allow an empty action attribute"
    html = render_to_string(create_element("form", {"action": "", "method": "post"}))
    assert "action" in html.lower()

    container = Container()
    root = create_root(container)
    root.render(create_element("form", {"action": "/submit", "method": "post"}))
    host = container.root.children[0]
    assert isinstance(host, ElementNode)
    assert host.props.get("action") == "/submit"

    root.render(create_element("form", {"action": "", "method": "get"}))
    host2 = container.root.children[0]
    assert host2 is host
    assert host2.props.get("action") == ""
