from __future__ import annotations

from ryact import create_element
from ryact_dom.server import render_to_string


def test_boolean_props_are_not_stringified_in_server_markup() -> None:
    # Upstream: DOMPropertyOperations-test.js — boolean props not stringified in attributes
    html = render_to_string(create_element("button", {"disabled": True, "type": "button"}))
    assert 'disabled="True"' not in html
    assert " disabled" in html or html.startswith("<button disabled") or "<button disabled>" in html
    assert "<button" in html
    assert "type=" in html
