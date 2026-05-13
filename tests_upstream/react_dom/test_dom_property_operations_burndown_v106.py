# Translated: DOMPropertyOperations-test.js — setValueForProperty basics (burndown v106)
from __future__ import annotations

from ryact import create_element
from ryact_dom.dom import Container, ElementNode
from ryact_dom.root import create_root
from ryact_dom.server import render_to_string


def test_sets_title_on_host_and_ssr() -> None:
    # Upstream: ``<div title="Tip!" />`` — default path uses the DOM ``title`` property / attribute.
    html = render_to_string(create_element("div", {"title": "Tip!"}))
    assert 'title="Tip!"' in html

    c = Container()
    root = create_root(c)
    root.render(create_element("div", {"title": "Tip!"}))
    h = c.root.children[0]
    assert isinstance(h, ElementNode)
    assert h.props.get("title") == "Tip!"


def test_sets_role_as_attribute_string() -> None:
    # Upstream: ``role`` is not an IDL property on HTML ``div``; React writes the attribute.
    html = render_to_string(create_element("div", {"role": "#"}))
    assert 'role="#"' in html

    c = Container()
    root = create_root(c)
    root.render(create_element("div", {"role": "#"}))
    h = c.root.children[0]
    assert isinstance(h, ElementNode)
    assert h.props.get("role") == "#"


def test_sets_xlink_href_namespace_attribute_on_svg_image() -> None:
    # Upstream: ``<image xlinkHref="about:blank" />`` inside an SVG namespace container.
    el = create_element(
        "svg",
        {"xmlns": "http://www.w3.org/2000/svg", "children": create_element("image", {"xlinkHref": "about:blank"})},
    )
    html = render_to_string(el)
    assert 'xlink:href="about:blank"' in html


def test_disabled_boolean_property_sequence() -> None:
    # Upstream: string ``disabled``, boolean true/false, null/undefined removal semantics.
    assert render_to_string(create_element("div", {"disabled": "disabled"})) == "<div disabled></div>"
    assert render_to_string(create_element("div", {"disabled": True})) == "<div disabled></div>"
    assert render_to_string(create_element("div", {"disabled": False})) == "<div></div>"

    c = Container()
    root = create_root(c)
    root.render(create_element("div", {"disabled": "disabled"}))
    h = c.root.children[0]
    assert isinstance(h, ElementNode)
    assert h.props.get("disabled") is True

    root.render(create_element("div", {"disabled": True}))
    assert h.props.get("disabled") is True

    root.render(create_element("div", {"disabled": False}))
    assert "disabled" not in h.props

    root.render(create_element("div", {"disabled": True}))
    root.render(create_element("div", {"disabled": None}))
    assert "disabled" not in h.props

    root.render(create_element("div", {"disabled": True}))
    # React ``undefined``: omit the prop entirely.
    root.render(create_element("div", {}))
    assert "disabled" not in h.props
