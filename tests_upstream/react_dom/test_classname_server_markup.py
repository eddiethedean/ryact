from __future__ import annotations

from ryact import create_element
from ryact_dom.server import render_to_string


def test_server_markup_merges_classname_to_class() -> None:
    # Upstream: ReactDOMComponent-test.js — "should generate the correct markup with className"
    html = render_to_string(create_element("div", {"className": "foo bar"}))
    assert 'class="foo bar"' in html or "class='foo bar'" in html
    assert "className" not in html
