from __future__ import annotations

from ryact import create_element
from ryact.concurrent import activity
from ryact_dom.server import render_to_string


def test_activity_can_be_rendered_in_react_server() -> None:
    """
    Upstream: ActivityReactServer-test.js
    - can be rendered in React Server
    """
    html = render_to_string(
        create_element(activity, {"mode": "visible", "children": create_element("div", {})})
    )
    assert html == "<div></div>"

    html2 = render_to_string(
        create_element(activity, {"mode": "hidden", "children": create_element("div", {})})
    )
    assert html2 == ""
