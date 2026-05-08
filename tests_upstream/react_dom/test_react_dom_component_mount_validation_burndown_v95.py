# Translated: ReactDOMComponent-test.js — mountComponent / updateComponent validation (burndown v95)
from __future__ import annotations

import warnings
from collections.abc import Iterator

import pytest
from ryact import create_element
from ryact.dev import is_dev
from ryact_dom.dom import Container
from ryact_dom.html_props import reset_dom_warning_state
from ryact_dom.root import create_root
from ryact_dom.server import render_to_string


@pytest.fixture(autouse=True)
def _reset_dom_warning_dedupe() -> Iterator[None]:
    reset_dom_warning_state()
    yield


def _assert_warn(rec: list[warnings.WarningMessage], needle: str) -> None:
    assert any(needle in str(w.message) for w in rec), [str(w.message) for w in rec]


def test_throws_when_dangerously_set_inner_html_not_object_shape_with_children() -> None:
    with pytest.raises(ValueError, match=r"props\.dangerouslySetInnerHTML"):
        render_to_string(
            create_element("div", {"children": "", "dangerouslySetInnerHTML": ""}),
        )


def test_warns_on_inner_html_prop_dev() -> None:
    if not is_dev():
        html = render_to_string(create_element("div", {"innerHTML": "<span>Hi</span>"}))
        assert "Hi" not in html or "<span>" not in html
        return
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        html = render_to_string(create_element("div", {"innerHTML": "<span>Hi</span>"}))
    _assert_warn(rec, "Directly setting property `innerHTML` is not permitted.")
    _assert_warn(rec, "    in div")


def test_warns_on_innerhtml_lowercase_dev() -> None:
    if not is_dev():
        render_to_string(create_element("div", {"innerhtml": "<span>Hi</span>"}))
        return
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        render_to_string(create_element("div", {"innerhtml": "<span>Hi</span>"}))
    _assert_warn(rec, "Directly setting property `innerHTML` is not permitted.")


def test_throws_when_dangerously_set_inner_html_is_string() -> None:
    with pytest.raises(ValueError, match=r"props\.dangerouslySetInnerHTML"):
        render_to_string(
            create_element("div", {"dangerouslySetInnerHTML": "<span>Hi</span>"}),
        )


def test_throws_when_dangerously_set_inner_html_object_missing__html() -> None:
    with pytest.raises(ValueError, match=r"props\.dangerouslySetInnerHTML"):
        render_to_string(create_element("div", {"dangerouslySetInnerHTML": {"foo": "bar"}}))


def test_warns_content_editable_with_text_child_dev() -> None:
    if not is_dev():
        render_to_string(create_element("div", {"contentEditable": True, "children": ""}))
        return
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        render_to_string(create_element("div", {"contentEditable": True, "children": ""}))
    _assert_warn(rec, "A component is `contentEditable` and contains `children`")
    _assert_warn(rec, "    in div")


def test_warns_content_editable_with_element_child_dev() -> None:
    if not is_dev():
        tree = create_element(
            "div",
            {"contentEditable": True},
            create_element("div"),
        )
        render_to_string(tree)
        return
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        tree = create_element(
            "div",
            {"contentEditable": True},
            create_element("div"),
        )
        render_to_string(tree)
    _assert_warn(rec, "A component is `contentEditable` and contains `children`")


def test_throws_when_style_is_string() -> None:
    with pytest.raises(ValueError, match=r"The `style` prop expects a mapping"):
        render_to_string(create_element("div", {"style": "display: none"}))


def test_update_warns_content_editable_with_nested_child_dev() -> None:
    if not is_dev():
        c = Container()
        root = create_root(c)
        root.render(create_element("div"))
        root.render(
            create_element("div", {"contentEditable": True}, create_element("div")),
        )
        return
    c = Container()
    root = create_root(c)
    root.render(create_element("div"))
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        root.render(
            create_element("div", {"contentEditable": True}, create_element("div")),
        )
    _assert_warn(rec, "A component is `contentEditable` and contains `children`")


def test_update_throws_when_children_and_dangerously_set_inner_html_both_set() -> None:
    c = Container()
    root = create_root(c)
    root.render(create_element("div"))
    with pytest.raises(ValueError, match="Can only set one of"):
        root.render(
            create_element(
                "div",
                {"children": "", "dangerouslySetInnerHTML": {"__html": ""}},
            ),
        )


def test_update_throws_invalid_style_after_initial_empty_div() -> None:
    c = Container()
    root = create_root(c)
    root.render(create_element("div"))
    with pytest.raises(ValueError, match=r"The `style` prop expects a mapping"):
        root.render(create_element("div", {"style": 1}))
