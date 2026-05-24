"""ReactDOMComponent-test.js parity: mutations, style, custom elements, DEV warnings (v132)."""

from __future__ import annotations

import warnings
from collections.abc import Iterator

import pytest
from ryact import create_element
from ryact.dev import is_dev
from ryact_dom.dom import Container, ElementNode
from ryact_dom.html_props import reset_dom_warning_state
from ryact_dom.root import create_root


@pytest.fixture(autouse=True)
def _reset_warning_dedupe() -> Iterator[None]:
    reset_dom_warning_state()
    yield


def _host(c: Container) -> ElementNode:
    h = c.root.children[0]
    assert isinstance(h, ElementNode)
    return h


class TemporalLike:
    def valueOf(self) -> object:
        raise TypeError("prod message")

    def __str__(self) -> str:
        return "2020-01-01"


def test_should_not_incur_unnecessary_dom_mutations_for_attributes() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("div", {"id": "host", "className": "foo"}))
    c.ops.clear()
    r.render(create_element("div", {"id": "host", "className": "foo"}))
    assert not any(op["op"] == "updateProps" for op in c.ops)
    r.render(create_element("div", {"id": "host", "className": "bar"}))
    assert sum(op["op"] == "updateProps" for op in c.ops) == 1
    c.ops.clear()
    r.render(create_element("div", {"id": "host", "className": "bar"}))
    assert not any(op["op"] == "updateProps" for op in c.ops)
    r.render(create_element("div", {"id": "host", "className": None}))
    assert sum(op["op"] == "updateProps" for op in c.ops) == 1
    c.ops.clear()
    r.render(create_element("div", {"id": "host", "className": "foo"}))
    assert sum(op["op"] == "updateProps" for op in c.ops) == 1
    c.ops.clear()
    r.render(create_element("div", {"id": "host"}))
    assert sum(op["op"] == "updateProps" for op in c.ops) == 1


def test_should_not_incur_unnecessary_dom_mutations_for_string_properties() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("div", {"slot": "a"}))
    c.ops.clear()
    for _ in range(3):
        r.render(create_element("div", {"slot": "a"}))
        assert not any(op["op"] == "updateProps" for op in c.ops)
    r.render(create_element("div", {"slot": "b"}))
    assert any(op["op"] == "updateProps" for op in c.ops)


def test_should_not_incur_unnecessary_dom_mutations_for_controlled_string_properties() -> None:
    c = Container()
    r = create_root(c)

    def _noop(_e: object) -> None:
        return None

    r.render(create_element("input", {"value": "a", "onChange": _noop}))
    c.ops.clear()
    r.render(create_element("input", {"value": "a", "onChange": _noop}))
    assert not any(op["op"] == "updateProps" for op in c.ops)
    r.render(create_element("input", {"value": "a", "onChange": _noop}))
    assert not any(op["op"] == "updateProps" for op in c.ops)


def test_should_not_incur_unnecessary_dom_mutations_for_boolean_properties() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("video", {"muted": True}))
    c.ops.clear()
    r.render(create_element("video", {"muted": True}))
    assert not any(op["op"] == "updateProps" for op in c.ops)
    r.render(create_element("video", {"muted": False}))
    assert any(op["op"] == "updateProps" for op in c.ops)


def test_should_not_update_styles_when_mutating_a_proxy_style_object() -> None:
    store = {"display": "none", "fontFamily": "Arial", "lineHeight": 1.2}

    class StyleProxy:
        @property
        def display(self) -> str:
            return store["display"]

        @property
        def fontFamily(self) -> str:
            return store["fontFamily"]

        @property
        def lineHeight(self) -> float:
            return store["lineHeight"]

    styles = StyleProxy()
    style_obj = {
        "display": styles.display,
        "fontFamily": styles.fontFamily,
        "lineHeight": styles.lineHeight,
    }
    c = Container()
    r = create_root(c)
    r.render(create_element("div", {"style": style_obj}))
    host = _host(c)
    assert host.style.display == "none"
    store["display"] = "block"
    r.render(create_element("div", {"style": style_obj}))
    assert host.style.display == "none"


@pytest.mark.skipif(not is_dev(), reason="frozen style objects are DEV-only")
def test_should_throw_when_mutating_style_objects() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("div", {"style": {"border": "1px solid black"}}))
    frozen = _host(c).props["style"]
    with pytest.raises(TypeError, match="frozen"):
        frozen["position"] = "absolute"


def test_throws_with_temporal_like_objects_as_style_values() -> None:
    c = Container()
    r = create_root(c)
    with pytest.raises(TypeError, match="prod message"):
        if is_dev():
            with warnings.catch_warnings(record=True):
                warnings.simplefilter("always")
                r.render(create_element("span", {"style": {"fontSize": TemporalLike()}}))
        else:
            r.render(create_element("span", {"style": {"fontSize": TemporalLike()}}))


def test_should_not_filter_attributes_for_custom_elements() -> None:
    c = Container()
    r = create_root(c)
    r.render(
        create_element(
            "x-foo-bar",
            {"action": "a", "formAction": "b", "href": "h", "src": "s"},
        ),
    )
    host = _host(c)
    assert host.has_attribute("action")
    assert host.has_attribute("formAction")
    assert host.has_attribute("href")
    assert host.has_attribute("src")


def test_should_not_apply_react_specific_aliases_to_custom_elements() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("x-el", {"arabicForm": "foo"}))
    host = _host(c)
    assert host.get_attribute("arabicForm") == "foo"
    assert not host.has_attribute("arabic-form")
    r.render(create_element("x-el", {"arabicForm": "boo"}))
    assert host.get_attribute("arabicForm") == "boo"
    r.render(create_element("x-el", {"acceptCharset": "buzz"}))
    assert not host.has_attribute("arabicForm")
    assert host.get_attribute("acceptCharset") == "buzz"
    assert not host.has_attribute("accept-charset")


def test_should_properly_update_custom_attributes_on_custom_elements() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("x-el", {"foo": "bar"}))
    host = _host(c)
    assert host.get_attribute("foo") == "bar"
    r.render(create_element("x-el", {"bar": "buzz"}))
    assert not host.has_attribute("foo")
    assert host.get_attribute("bar") == "buzz"


def test_should_update_arbitrary_attributes_for_tags_containing_dashes() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("x-foo-component", None))
    r.render(create_element("x-foo-component", {"myAttr": "myval"}))
    assert _host(c).get_attribute("myAttr") == "myval"


def test_should_skip_dangerously_set_innerhtml_on_web_components() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("x-el", {"dangerouslySetInnerHTML": "ignored"}))
    assert not _host(c).has_attribute("dangerouslySetInnerHTML")
    r.render(create_element("x-el", {"dangerously_set_inner_html": "ignored"}))
    assert not _host(c).has_attribute("dangerously_set_inner_html")


def test_should_skip_reserved_props_on_web_components() -> None:
    c = Container()
    r = create_root(c)
    r.render(
        create_element(
            "x-el",
            {
                "children": "nope",
                "suppressContentEditableWarning": True,
                "suppressHydrationWarning": True,
            },
        ),
    )
    host = _host(c)
    assert not host.has_attribute("children")
    assert not host.has_attribute("suppressContentEditableWarning")
    assert not host.has_attribute("suppressHydrationWarning")


def test_should_transition_from_children_to_innerhtml_in_nested_el() -> None:
    c = Container()
    r = create_root(c)
    r.render(
        create_element(
            "div",
            None,
            create_element("div", None, "adieu"),
        ),
    )
    inner = _host(c).children[0]
    assert isinstance(inner, ElementNode)
    assert inner.children[0].text == "adieu"  # type: ignore[union-attr]
    r.render(
        create_element(
            "div",
            None,
            create_element("div", {"dangerouslySetInnerHTML": {"__html": "bonjour"}}),
        ),
    )
    inner2 = _host(c).children[0]
    assert isinstance(inner2, ElementNode)
    assert inner2.innerHTML == "bonjour"


def test_should_transition_from_innerhtml_to_children_in_nested_el() -> None:
    c = Container()
    r = create_root(c)
    r.render(
        create_element(
            "div",
            None,
            create_element("div", {"dangerouslySetInnerHTML": {"__html": "bonjour"}}),
        ),
    )
    inner = _host(c).children[0]
    assert isinstance(inner, ElementNode)
    assert inner.innerHTML == "bonjour"
    r.render(
        create_element(
            "div",
            None,
            create_element("div", None, "adieu"),
        ),
    )
    inner2 = _host(c).children[0]
    assert isinstance(inner2, ElementNode)
    text = inner2.children[0]
    from ryact_dom.dom import TextNode

    assert isinstance(text, TextNode)
    assert text.text == "adieu"


@pytest.mark.skipif(not is_dev(), reason="invalid prop DEV warnings")
def test_should_warn_for_unknown_prop() -> None:
    c = Container()
    r = create_root(c)
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        r.render(create_element("div", {"foo": lambda: None}))
    assert any("Invalid value for prop `foo`" in str(w.message) for w in rec)


@pytest.mark.skipif(not is_dev(), reason="invalid prop DEV warnings")
def test_should_group_multiple_unknown_prop_warnings_together() -> None:
    c = Container()
    r = create_root(c)
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        r.render(create_element("div", {"foo": lambda: None, "baz": lambda: None}))
    msgs = [str(w.message) for w in rec]
    assert any("Invalid values for props `foo`, `baz`" in m for m in msgs)


@pytest.mark.skipif(not is_dev(), reason="event handler DEV warnings")
def test_should_warn_for_ondblclick_prop() -> None:
    c = Container()
    r = create_root(c)
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        r.render(create_element("div", {"onDblClick": lambda _e: None}))
    assert any("onDblClick" in str(w.message) and "onDoubleClick" in str(w.message) for w in rec)


@pytest.mark.skipif(not is_dev(), reason="event handler DEV warnings")
def test_should_warn_for_unknown_string_event_handlers() -> None:
    c = Container()
    r = create_root(c)
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        r.render(create_element("div", {"onUnknown": "not-a-function"}))
        r.render(create_element("div", {"onunknown": "x"}))
        r.render(create_element("div", {"on-unknown": "x"}))
    msgs = [str(w.message) for w in rec]
    assert sum("Unknown event handler property" in m for m in msgs) == 3
    host = _host(c)
    assert not host.has_attribute("on-unknown")


@pytest.mark.skipif(not is_dev(), reason="event handler DEV warnings")
def test_should_warn_for_unknown_function_event_handlers() -> None:
    c = Container()
    r = create_root(c)

    def _fn(_e: object) -> None:
        return None

    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        r.render(create_element("div", {"onUnknown": _fn}))
    assert any("Unknown event handler property `onUnknown`" in str(w.message) for w in rec)


@pytest.mark.skipif(not is_dev(), reason="DOM property DEV warnings")
def test_should_warn_for_badly_cased_react_attributes() -> None:
    c = Container()
    r = create_root(c)
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        r.render(create_element("div", {"CHILDREN": "5"}))
    assert any("CHILDREN" in str(w.message) and "children" in str(w.message) for w in rec)
    assert _host(c).get_attribute("CHILDREN") == "5"


@pytest.mark.skipif(not is_dev(), reason="is attribute DEV warnings")
def test_should_warn_about_non_string_is_attribute() -> None:
    c = Container()
    r = create_root(c)
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        r.render(create_element("button", {"is": lambda: None}))
    assert any("function` for a string attribute `is`" in str(w.message) for w in rec)


def test_should_ignore_attribute_list_for_elements_with_the_is_attribute() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("div", {"is": "x-custom", "cowabunga": "radical"}))
    host = _host(c)
    assert host.has_attribute("cowabunga")
