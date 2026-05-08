# Translated: ReactDOMComponent-test.js — Attributes with aliases (burndown v94)
from __future__ import annotations

import warnings
from collections.abc import Iterator

import pytest
from ryact import create_element
from ryact.dev import is_dev
from ryact_dom.dom import Container, ElementNode
from ryact_dom.html_props import html_attribute_name, reset_dom_warning_state
from ryact_dom.root import create_root
from ryact_dom.server import render_to_string


@pytest.fixture(autouse=True)
def _reset_dom_warning_dedupe() -> Iterator[None]:
    reset_dom_warning_state()
    yield


def _assert_any_warning(rec: list[warnings.WarningMessage], needle: str) -> None:
    assert any(needle in str(w.message) for w in rec), [str(w.message) for w in rec]


def test_sets_aliased_attributes_on_html_attributes_dev_warns_class() -> None:
    if not is_dev():
        html = render_to_string(create_element("div", {"class": "test"}))
        assert 'class="test"' in html
    else:
        with warnings.catch_warnings(record=True) as rec:
            warnings.simplefilter("always")
            html = render_to_string(create_element("div", {"class": "test"}))
        _assert_any_warning(rec, "Invalid DOM property `class`. Did you mean `className`?")
        _assert_any_warning(rec, "    in div")
    assert 'class="test"' in html

    c = Container()
    root = create_root(c)
    root.render(create_element("div", {"class": "test"}))
    el = c.root.children[0]
    assert isinstance(el, ElementNode)
    assert el.props.get("class") == "test"


def _svg_text_node_after_render(container: Container) -> ElementNode:
    svg = container.root.children[0]
    assert isinstance(svg, ElementNode)
    assert svg.tag == "svg"
    text_el = svg.children[0]
    assert isinstance(text_el, ElementNode)
    assert text_el.tag == "text"
    return text_el


def test_sets_incorrectly_cased_class_on_html_dev_warns() -> None:
    if not is_dev():
        html = render_to_string(create_element("div", {"cLASS": "test"}))
        assert 'class="test"' in html
    else:
        with warnings.catch_warnings(record=True) as rec:
            warnings.simplefilter("always")
            html = render_to_string(create_element("div", {"cLASS": "test"}))
        _assert_any_warning(rec, "Invalid DOM property `cLASS`. Did you mean `className`?")
        _assert_any_warning(rec, "    in div")
    assert 'class="test"' in html


def test_sets_aliased_attributes_on_svg_text_with_warning() -> None:
    tree = create_element(
        "svg",
        None,
        create_element("text", {"arabic-form": "initial"}),
    )
    if not is_dev():
        html = render_to_string(tree)
        assert 'arabic-form="initial"' in html
    else:
        with warnings.catch_warnings(record=True) as rec:
            warnings.simplefilter("always")
            html = render_to_string(tree)
        _assert_any_warning(rec, "Invalid DOM property `arabic-form`. Did you mean `arabicForm`?")
        _assert_any_warning(rec, "    in text")
    assert 'arabic-form="initial"' in html

    c = Container()
    root = create_root(c)
    root.render(tree)
    text_el = _svg_text_node_after_render(c)
    assert any(
        html_attribute_name(k) == "arabic-form" and text_el.props.get(k) == "initial"
        for k in text_el.props
        if k != "children"
    )


def test_sets_aliased_attributes_on_customized_builtin_div() -> None:
    if not is_dev():
        html = render_to_string(create_element("div", {"is": "custom-element", "class": "test"}))
        assert 'class="test"' in html
    else:
        with warnings.catch_warnings(record=True) as rec:
            warnings.simplefilter("always")
            html = render_to_string(create_element("div", {"is": "custom-element", "class": "test"}))
        assert not any("className" in str(w.message) for w in rec)
    assert 'class="test"' in html


def test_aliased_attributes_on_customized_builtin_div_bad_casing() -> None:
    if not is_dev():
        html = render_to_string(create_element("div", {"is": "custom-element", "claSS": "test"}))
        assert 'class="test"' in html
    else:
        with warnings.catch_warnings(record=True) as rec:
            warnings.simplefilter("always")
            html = render_to_string(create_element("div", {"is": "custom-element", "claSS": "test"}))
        assert not any("className" in str(w.message) for w in rec)
    assert 'class="test"' in html


def test_updates_class_on_customized_builtin_div_host() -> None:
    c = Container()
    root = create_root(c)
    root.render(create_element("div", {"is": "custom-element", "class": "foo"}))
    root.render(create_element("div", {"is": "custom-element", "class": "bar"}))
    el = c.root.children[0]
    assert isinstance(el, ElementNode)
    assert el.props.get("class") == "bar"
