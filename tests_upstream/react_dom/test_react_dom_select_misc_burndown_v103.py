# Translated subset: ReactDOMSelect-test.js — SSR option DSH, dynamic labels, exact multi value, remount smoke
from __future__ import annotations

import re
from collections.abc import Iterator

import pytest
from ryact import create_element
from ryact.element import UNDEFINED
from ryact_dom.dom import Container, ElementNode, TextNode
from ryact_dom.root import create_root
from ryact_dom.server import render_to_string


@pytest.fixture(autouse=True)
def _dev_only_guards() -> Iterator[None]:
    yield


def _options_from_dom(container: Container) -> list[tuple[str, bool]]:
    sel = container.root.children[0]
    assert isinstance(sel, ElementNode)
    assert sel.tag.lower() == "select"
    out: list[tuple[str, bool]] = []

    def walk(node: ElementNode) -> None:
        for ch in node.children:
            if isinstance(ch, ElementNode) and ch.tag.lower() == "option":
                v = ch.props.get("value")
                if v is None and ch.children and isinstance(ch.children[0], TextNode):
                    v = ch.children[0].text
                sv = "" if v is None else str(v)
                out.append((sv, bool(ch.props.get("selected"))))
            elif isinstance(ch, ElementNode) and ch.tag.lower() == "optgroup":
                walk(ch)

    walk(sel)
    return out


def _dynamic_option_children(val: str):
    return (
        create_element(
            "option",
            {"key": "monkey", "value": "monkey"},
            "A monkey ",
            "is chosen" if val == "monkey" else "",
            "!",
        ),
        create_element(
            "option",
            {"key": "giraffe", "value": "giraffe"},
            "A giraffe ",
            "is chosen" if val == "giraffe" else "",
            "!",
        ),
        create_element(
            "option",
            {"key": "gorilla", "value": "gorilla"},
            "A gorilla ",
            "is chosen" if val == "gorilla" else "",
            "!",
        ),
    )


def test_ssr_select_options_use_dangerously_set_inner_html() -> None:
    html = render_to_string(
        create_element(
            "select",
            {"defaultValue": "giraffe"},
            create_element(
                "option",
                {"value": "monkey", "dangerouslySetInnerHTML": {"__html": "A monkey!"}},
            ),
            create_element(
                "option",
                {"value": "giraffe", "dangerouslySetInnerHTML": {"__html": "A giraffe!"}},
            ),
            create_element(
                "option",
                {"value": "gorilla", "dangerouslySetInnerHTML": {"__html": "A gorilla!"}},
            ),
        ),
    )
    assert re.search(r'<option[^>]*value="monkey"[^>]*>', html)
    assert "A monkey!" in html
    assert re.search(r'<option[^>]*value="giraffe"[^>]*selected', html)
    assert re.search(r'<option[^>]*value="gorilla"[^>]*>', html)
    assert html.count("selected") == 1


def test_controlled_select_dynamic_option_label_children() -> None:
    c = Container()
    root = create_root(c)
    root.render(
        create_element(
            "select",
            {"value": "monkey", "onChange": lambda e: None},
            *_dynamic_option_children("monkey"),
        ),
    )
    assert _options_from_dom(c) == [("monkey", True), ("giraffe", False), ("gorilla", False)]
    root.render(
        create_element(
            "select",
            {"value": "giraffe", "onChange": lambda e: None},
            *_dynamic_option_children("giraffe"),
        ),
    )
    assert _options_from_dom(c) == [("monkey", False), ("giraffe", True), ("gorilla", False)]


def test_multiple_value_matches_entire_token_not_prefix() -> None:
    c = Container()
    root = create_root(c)
    root.render(
        create_element(
            "select",
            {"multiple": True, "value": ("12",), "onChange": lambda e: None},
            create_element("option", {"value": "1"}, "one"),
            create_element("option", {"value": "2"}, "two"),
            create_element("option", {"value": "12"}, "twelve"),
        ),
    )
    assert _options_from_dom(c) == [("1", False), ("2", False), ("12", True)]


def test_empty_select_then_fresh_root_with_undefined_value() -> None:
    """Upstream title mentions textarea; body is select remount / undefined value smoke."""
    c1 = Container()
    r1 = create_root(c1)
    r1.render(create_element("select"))
    sel1 = c1.root.children[0]
    assert isinstance(sel1, ElementNode)
    assert sel1.tag.lower() == "select"
    assert sel1.children == []
    c2 = Container()
    r2 = create_root(c2)
    r2.render(create_element("select", {"value": UNDEFINED}, create_element("option", {"value": "x"}, "x")))
    sel = c2.root.children[0]
    assert isinstance(sel, ElementNode)
    assert sel.tag.lower() == "select"
