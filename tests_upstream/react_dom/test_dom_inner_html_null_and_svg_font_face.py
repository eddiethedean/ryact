from __future__ import annotations

import warnings

from ryact import create_element
from ryact.dev import is_dev
from ryact_dom.dom import Container, ElementNode
from ryact_dom.root import create_root
from ryact_dom.server import render_to_string


def test_dangerously_set_inner_html_null_does_not_throw_server_or_client() -> None:
    # Upstream: ReactDOMComponent-test.js — mountComponent — "should allow {__html: null}"
    html = render_to_string(
        create_element("div", {"dangerouslySetInnerHTML": {"__html": None}}),
    )
    assert html == "<div></div>"

    container = Container()
    root = create_root(container)
    root.render(create_element("div", {"dangerouslySetInnerHTML": {"__html": None}}))
    host = container.root.children[0]
    assert isinstance(host, ElementNode)
    assert "dangerouslySetInnerHTML" not in host.props


def test_svg_font_face_element_is_not_a_custom_element_x_height_casing() -> None:
    # Upstream: ReactDOMComponent-test.js — Hyphenated SVG elements
    # "the font-face element is not a custom element"
    if not is_dev():
        return
    container = Container()
    root = create_root(container)
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        root.render(
            create_element(
                "svg",
                None,
                create_element("font-face", {"x-height": False}),
            ),
        )
    msgs = [str(m.message) for m in rec]
    assert any("x-height" in m and "xHeight" in m for m in msgs)
    svg = container.root.children[0]
    assert isinstance(svg, ElementNode)
    ff = svg.children[0]
    assert isinstance(ff, ElementNode)
    assert ff.tag == "font-face"
    assert "x-height" not in ff.props
