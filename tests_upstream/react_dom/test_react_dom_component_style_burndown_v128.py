"""ReactDOMComponent-test.js parity: client ``style`` + innerHTML + aliases (v128)."""

from __future__ import annotations

import math
import warnings

import pytest
from ryact import create_element
from ryact.dev import is_dev
from ryact_dom.dom import Container, ElementNode
from ryact_dom.root import create_root


def _host(c: Container) -> ElementNode:
    h = c.root.children[0]
    assert isinstance(h, ElementNode)
    return h


def test_should_clear_a_single_style_prop_when_changing_style() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("div", {"style": {"display": "none", "color": "red"}}))
    host = _host(c)
    r.render(create_element("div", {"style": {"color": "green"}}))
    assert host.style.display == ""
    assert host.style.color == "green"


def test_should_clear_all_the_styles_when_removing_style() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("div", {"style": {"display": "none", "color": "red"}}))
    host = _host(c)
    r.render(create_element("div", {}))
    assert host.style.display == ""
    assert host.style.color == ""


def test_should_update_styles_when_style_changes_from_null_to_object() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("div", {"style": {"color": "red"}}))
    host = _host(c)
    assert host.style.color == "red"
    r.render(create_element("div", {}))
    assert host.style.color == ""
    r.render(create_element("div", {"style": {"color": "red"}}))
    assert host.style.color == "red"


def test_should_update_styles_if_initially_null() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("div", {}))
    host = _host(c)
    r.render(create_element("div", {"style": {"color": "red"}}))
    assert host.style.color == "red"


def test_should_update_styles_if_updated_to_null_multiple_times() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("div", {"style": {"color": "red"}}))
    host = _host(c)
    r.render(create_element("div", {"style": None}))
    assert host.style.color == ""
    r.render(create_element("div", {"style": None}))
    assert host.style.color == ""


def test_should_gracefully_handle_various_style_value_types() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("div", {"style": {}}))
    host = _host(c)
    r.render(
        create_element(
            "div",
            {"style": {"display": "block", "left": "1px", "top": 2, "fontFamily": "Arial"}},
        )
    )
    assert host.style.display == "block"
    assert host.style.left == "1px"
    assert host.style.top == "2px"
    assert host.style.fontFamily == "Arial"
    r.render(create_element("div", {"style": {"display": "", "left": None, "top": False, "fontFamily": True}}))
    assert host.style.display == ""
    assert host.style.left == ""
    assert host.style.top == ""
    assert host.style.fontFamily == ""


@pytest.mark.skipif(not is_dev(), reason="unitless zero margin DEV check")
def test_should_not_warn_for_0_as_a_unitless_style_value() -> None:
    c = Container()
    r = create_root(c)
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        r.render(create_element("div", {"style": {"margin": "0"}}))
    assert not any("css style property" in str(w.message) for w in rec)


@pytest.mark.skipif(not is_dev(), reason="NaN style DEV warning")
def test_should_warn_nicely_about_nan_in_style() -> None:
    c = Container()
    r = create_root(c)
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        r.render(create_element("span", {"style": {"fontSize": math.nan}}))
    assert any("`NaN` is an invalid value for the `fontSize` css style property" in str(w.message) for w in rec)


def test_should_empty_element_when_removing_innerhtml() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("div", {"dangerouslySetInnerHTML": {"__html": ":)"}}))
    host = _host(c)
    assert host.innerHTML == ":)"
    r.render(create_element("div", {}))
    assert host.innerHTML == ""


def test_should_transition_from_string_content_to_innerhtml() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("div", {}, "hello"))
    host = _host(c)
    assert host.innerHTML == "hello"
    r.render(create_element("div", {"dangerouslySetInnerHTML": {"__html": "goodbye"}}))
    assert host.innerHTML == "goodbye"


def test_should_transition_from_innerhtml_to_string_content() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("div", {"dangerouslySetInnerHTML": {"__html": "bonjour"}}))
    host = _host(c)
    assert host.innerHTML == "bonjour"
    r.render(create_element("div", {}, "adieu"))
    assert host.innerHTML == "adieu"


def test_should_not_reset_innerhtml_for_when_children_is_null() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("div", {}))
    host = _host(c)
    host.innerHTML = "bonjour"
    r.render(create_element("div", {}))
    assert host.innerHTML == "bonjour"


def test_should_apply_react_specific_aliases_to_html_elements() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("form", {"acceptCharset": "foo"}))
    host = _host(c)
    assert host.getAttribute("accept-charset") == "foo"
    assert not host.hasAttribute("acceptCharset")
    r.render(create_element("form", {"acceptCharset": "boo"}))
    assert host.getAttribute("accept-charset") == "boo"
    r.render(create_element("form", {"acceptCharset": None}))
    assert not host.hasAttribute("accept-charset")
    r.render(create_element("form", {"acceptCharset": "foo"}))
    r.render(create_element("form", {}))
    assert not host.hasAttribute("accept-charset")


def test_should_apply_react_specific_aliases_to_svg_elements() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("svg", {"arabicForm": "foo"}))
    host = _host(c)
    assert host.getAttribute("arabic-form") == "foo"
    assert not host.hasAttribute("arabicForm")
    r.render(create_element("svg", {"arabicForm": "boo"}))
    assert host.getAttribute("arabic-form") == "boo"
    r.render(create_element("svg", {"arabicForm": None}))
    assert not host.hasAttribute("arabic-form")


def test_should_remove_attributes() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("img", {"height": "17"}))
    host = _host(c)
    assert host.has_attribute("height")
    r.render(create_element("img", {}))
    assert not host.has_attribute("height")


def test_should_remove_properties() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("div", {"className": "monkey"}))
    host = _host(c)
    assert host.className == "monkey"
    r.render(create_element("div", {}))
    assert host.className == ""
