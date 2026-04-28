from __future__ import annotations

from ryact import create_element
from ryact_dom import render_to_string


def test_should_handle_dangerouslysetinnerhtml() -> None:
    html = render_to_string(
        create_element("div", {"dangerouslySetInnerHTML": {"__html": "<span>Hi</span>"}})
    )
    assert html == "<div><span>Hi</span></div>"


def test_should_escape_style_names_and_values() -> None:
    html = render_to_string(
        create_element("div", {"style": {"backgroundImage": 'url("javascript:alert(1)")'}})
    )
    assert 'background-image:url(&quot;javascript:alert(1)&quot;)' in html

