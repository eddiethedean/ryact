from __future__ import annotations

import pytest

from ryact import create_element
from ryact_dom.dom import Container
from ryact_dom.root import create_root
from ryact_dom.server import render_to_string


def test_should_throw_for_children_on_void_elements() -> None:
    with pytest.raises(ValueError):
        _ = render_to_string(create_element("input", {"children": ["x"]}))

    root = create_root(Container())
    with pytest.raises(ValueError):
        root.render(create_element("input", {"children": ["x"]}))


def test_should_throw_on_children_for_void_elements() -> None:
    # Same semantic as above, but keep a distinct upstream case.
    with pytest.raises(ValueError):
        _ = render_to_string(create_element("br", {"children": ["x"]}))


def test_should_throw_on_dangerouslysetinnerhtml_for_void_elements() -> None:
    with pytest.raises(ValueError):
        _ = render_to_string(create_element("img", {"dangerouslySetInnerHTML": {"__html": "x"}}))

    root = create_root(Container())
    with pytest.raises(ValueError):
        root.render(create_element("img", {"dangerouslySetInnerHTML": {"__html": "x"}}))


def test_should_treat_menuitem_as_a_void_element_but_still_create_the_closing_tag() -> None:
    html = render_to_string(create_element("menuitem", {}))
    assert html == "<menuitem></menuitem>"

