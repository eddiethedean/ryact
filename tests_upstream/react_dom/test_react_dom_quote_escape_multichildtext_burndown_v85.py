# Translated: quoteAttributeValueForBrowser-test.js, escapeTextForBrowser-test.js,
# ReactMultiChildText-test.js (burndown v85 subset).
from __future__ import annotations

import re

import pytest
from ryact import create_element
from ryact_dom.dom import Container, ElementNode, TextNode
from ryact_dom.root import create_root
from ryact_dom.server import render_to_string


def _assert_img_attr_matches(html: str, expected_attr_fragment: str) -> None:
    assert re.search(r"<img\b[^>]*" + re.escape(expected_attr_fragment), html, re.I)


def test_quote_ampersand_escaped_inside_attributes() -> None:
    html = render_to_string(create_element("img", {"data_attr": "&"}))
    _assert_img_attr_matches(html, 'data-attr="&amp;"')


def test_quote_double_quote_escaped_inside_attributes() -> None:
    html = render_to_string(create_element("img", {"data_attr": '"'}))
    _assert_img_attr_matches(html, 'data-attr="&quot;"')


def test_quote_single_quote_escaped_inside_attributes() -> None:
    html = render_to_string(create_element("img", {"data_attr": "'"}))
    _assert_img_attr_matches(html, 'data-attr="&#x27;"')


def test_quote_greater_than_escaped_inside_attributes() -> None:
    html = render_to_string(create_element("img", {"data_attr": ">"}))
    _assert_img_attr_matches(html, 'data-attr="&gt;"')


def test_quote_lower_than_escaped_inside_attributes() -> None:
    html = render_to_string(create_element("img", {"data_attr": "<"}))
    _assert_img_attr_matches(html, 'data-attr="&lt;"')


def test_quote_number_stringified_inside_attributes() -> None:
    html = render_to_string(create_element("img", {"data_attr": 42}))
    _assert_img_attr_matches(html, 'data-attr="42"')


def test_quote_object_to_string_inside_attributes() -> None:
    class Sample:
        def __str__(self) -> str:
            return "ponys"

    html = render_to_string(create_element("img", {"data_attr": Sample()}))
    _assert_img_attr_matches(html, 'data-attr="ponys"')


def test_quote_script_like_string_escaped_inside_attributes() -> None:
    payload = "<script type='' src=\"\"></script>"
    html = render_to_string(create_element("img", {"data_attr": payload}))
    assert "&lt;script" in html
    assert "type=&#x27;&#x27;" in html
    assert "src=&quot;&quot;" in html
    assert "&lt;/script&gt;" in html


def test_escape_ampersand_in_text() -> None:
    html = render_to_string(create_element("span", None, "&"))
    assert "<span>&amp;</span>" in html


def test_escape_double_quote_in_text() -> None:
    html = render_to_string(create_element("span", None, '"'))
    assert "<span>&quot;</span>" in html


def test_escape_single_quote_in_text() -> None:
    html = render_to_string(create_element("span", None, "'"))
    assert "<span>&#x27;</span>" in html


def test_escape_greater_than_in_text() -> None:
    html = render_to_string(create_element("span", None, ">"))
    assert "<span>&gt;</span>" in html


def test_escape_lower_than_in_text() -> None:
    html = render_to_string(create_element("span", None, "<"))
    assert "<span>&lt;</span>" in html


def test_escape_number_text_content() -> None:
    html = render_to_string(create_element("span", None, 42))
    assert "<span>42</span>" in html


def test_escape_number_on_attribute_via_img() -> None:
    html = render_to_string(create_element("img", {"data_attr": 42}))
    _assert_img_attr_matches(html, 'data-attr="42"')


def test_escape_script_like_text_content() -> None:
    payload = "<script type='' src=\"\"></script>"
    html = render_to_string(create_element("span", None, payload))
    assert "<span>&lt;script type=&#x27;&#x27; " in html
    assert "src=&quot;&quot;&gt;&lt;/script&gt;</span>" in html


def test_multichild_bigint_text_render_and_update() -> None:
    n = 10**40
    html = render_to_string(create_element("div", None, n))
    assert str(n) in html

    c = Container()
    root = create_root(c)
    root.render(create_element("div", None, n))
    h = c.root.children[0]
    assert isinstance(h, ElementNode)
    t0 = h.children[0]
    assert isinstance(t0, TextNode)
    assert t0.text == str(n)

    m = n + 1
    root.render(create_element("div", None, m))
    h1 = c.root.children[0]
    assert isinstance(h1, ElementNode)
    t1 = h1.children[0]
    assert isinstance(t1, TextNode)
    assert t1.text == str(m)


def test_multichild_throw_when_dangerously_set_inner_html_and_children() -> None:
    with pytest.raises(ValueError, match="dangerouslySetInnerHTML"):
        render_to_string(
            create_element(
                "div",
                {
                    "dangerouslySetInnerHTML": {"__html": "abcdef"},
                    "children": ("ghjkl",),
                },
            ),
        )

    root = create_root(Container())
    with pytest.raises(ValueError, match="dangerouslySetInnerHTML"):
        root.render(
            create_element(
                "div",
                {
                    "dangerouslySetInnerHTML": {"__html": "abcdef"},
                    "children": ("ghjkl",),
                },
            ),
        )


def test_multichild_nested_heading_with_text_children() -> None:
    c = Container()
    root = create_root(c)
    root.render(
        create_element(
            "div",
            None,
            create_element("h1", None, create_element("span"), create_element("span")),
        ),
    )
    root.render(create_element("div", None, create_element("h1", None, "A")))
    root.render(create_element("div", None, create_element("h1", None, ("A",))))
    root.render(create_element("div", None, create_element("h1", None, ("A", "B"))))
    assert isinstance(c.root.children[0], ElementNode)
