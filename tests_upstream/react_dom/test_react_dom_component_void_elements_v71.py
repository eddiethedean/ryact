from __future__ import annotations

import pytest
from ryact import create_element
from ryact_dom.dom import Container
from ryact_dom.root import create_root
from ryact_dom.server import render_to_string

_EXPECT_VOID = (
    "is a void element tag and must neither have `children` nor use `dangerouslySetInnerHTML`."
)


def test_should_throw_for_children_on_void_elements() -> None:
    with pytest.raises(ValueError, match=_EXPECT_VOID):
        _ = render_to_string(create_element("input", {"children": ["x"]}))

    root = create_root(Container())
    with pytest.raises(ValueError, match=_EXPECT_VOID):
        root.render(create_element("input", {"children": ["x"]}))


def test_should_throw_on_children_for_void_elements() -> None:
    # Same semantic as above, but keep a distinct upstream case.
    with pytest.raises(ValueError, match=_EXPECT_VOID):
        _ = render_to_string(create_element("br", {"children": ["x"]}))


def test_should_throw_on_dangerouslysetinnerhtml_for_void_elements() -> None:
    with pytest.raises(ValueError, match=_EXPECT_VOID):
        _ = render_to_string(create_element("img", {"dangerouslySetInnerHTML": {"__html": "x"}}))

    root = create_root(Container())
    with pytest.raises(ValueError, match=_EXPECT_VOID):
        root.render(create_element("img", {"dangerouslySetInnerHTML": {"__html": "x"}}))


def test_update_void_input_rejects_children_after_mount() -> None:
    root = create_root(Container())
    root.render(create_element("input", None))
    with pytest.raises(ValueError, match=_EXPECT_VOID):
        root.render(create_element("input", None, "x"))


def test_update_void_input_rejects_dangerously_set_inner_html_after_mount() -> None:
    root = create_root(Container())
    root.render(create_element("input", None))
    with pytest.raises(ValueError, match=_EXPECT_VOID):
        root.render(create_element("input", {"dangerouslySetInnerHTML": {"__html": "x"}}))


def test_should_treat_menuitem_as_a_void_element_but_still_create_the_closing_tag() -> None:
    html = render_to_string(create_element("menuitem", {}))
    assert html == "<menuitem></menuitem>"
