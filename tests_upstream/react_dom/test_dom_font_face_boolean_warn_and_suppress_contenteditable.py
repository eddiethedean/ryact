from __future__ import annotations

import warnings

from ryact import create_element
from ryact.dev import is_dev
from ryact_dom.dom import Container, ElementNode
from ryact_dom.root import create_root


def test_font_face_does_not_allow_unknown_boolean_values() -> None:
    # Upstream: ReactDOMComponent-test.js — Hyphenated SVG elements
    # "the font-face element does not allow unknown boolean values"
    container = Container()
    root = create_root(container)
    if is_dev():
        with warnings.catch_warnings(record=True) as rec:
            warnings.simplefilter("always")
            root.render(
                create_element(
                    "svg",
                    None,
                    create_element("font-face", {"whatever": False}),
                ),
            )
        msgs = [str(m.message) for m in rec]
        assert any("whatever" in m and "non-boolean" in m for m in msgs)
    else:
        root.render(
            create_element(
                "svg",
                None,
                create_element("font-face", {"whatever": False}),
            ),
        )
    svg = container.root.children[0]
    assert isinstance(svg, ElementNode)
    ff = svg.children[0]
    assert isinstance(ff, ElementNode)
    assert ff.tag == "font-face"
    assert "whatever" not in ff.props


def test_div_respects_suppress_content_editable_warning() -> None:
    # Upstream: ReactDOMComponent-test.js — mountComponent
    # "should respect suppressContentEditableWarning"
    container = Container()
    root = create_root(container)
    root.render(
        create_element(
            "div",
            {"contentEditable": True, "suppressContentEditableWarning": True},
            "",
        ),
    )
    host = container.root.children[0]
    assert isinstance(host, ElementNode)
    assert "suppressContentEditableWarning" not in host.props
    assert "suppress_content_editable_warning" not in host.props
    assert host.props.get("contentEditable") is True
