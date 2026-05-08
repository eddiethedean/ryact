# Translated: ReactDOMComponent-test.js — nesting validation (prop / event casing) burndown v97
from __future__ import annotations

import warnings
from collections.abc import Iterator

import pytest
from ryact import create_element
from ryact.dev import is_dev
from ryact_dom.dom import Container, ElementNode
from ryact_dom.html_props import reset_dom_warning_state
from ryact_dom.root import create_root
from ryact_dom.server import render_to_string


@pytest.fixture(autouse=True)
def _reset_dom_warning_dedupe() -> Iterator[None]:
    reset_dom_warning_state()
    yield


def _assert_warn(rec: list[warnings.WarningMessage], needle: str) -> None:
    assert any(needle in str(w.message) for w in rec), [str(w.message) for w in rec]


@pytest.mark.skipif(not is_dev(), reason="nesting validation DEV warnings are DEV-only")
def test_suggest_property_name_if_available_client() -> None:
    c = Container()
    root = create_root(c)
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        root.render(create_element("label", {"for": "test"}))
        _assert_warn(rec, "Invalid DOM property `for`. Did you mean `htmlFor`?")
        _assert_warn(rec, "    in label")

        label = c.root.children[0]
        assert isinstance(label, ElementNode)
        assert label.props.get("htmlFor") == "test"

        rec.clear()
        root.render(create_element("input", {"type": "text", "autofocus": True}))
        _assert_warn(rec, "Invalid DOM property `autofocus`. Did you mean `autoFocus`?")
        _assert_warn(rec, "    in input")
    inp = c.root.children[0]
    assert isinstance(inp, ElementNode)
    assert inp.props.get("autoFocus") is True


@pytest.mark.skipif(not is_dev(), reason="nesting validation DEV warnings are DEV-only")
def test_suggest_property_name_if_available_ssr() -> None:
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        render_to_string(create_element("label", {"for": "test"}))
        _assert_warn(rec, "Invalid DOM property `for`. Did you mean `htmlFor`?")
        _assert_warn(rec, "    in label")

        rec.clear()
        render_to_string(create_element("input", {"type": "text", "autofocus": True}))
        _assert_warn(rec, "Invalid DOM property `autofocus`. Did you mean `autoFocus`?")
        _assert_warn(rec, "    in input")


def test_suggest_property_name_markup_uses_html_attribute_names() -> None:
    html = render_to_string(create_element("label", {"for": "test"}))
    assert 'for="test"' in html


@pytest.mark.skipif(not is_dev(), reason="nesting validation DEV warnings are DEV-only")
def test_warn_about_class_client() -> None:
    c = Container()
    root = create_root(c)
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        root.render(create_element("div", {"class": "muffins"}))
    _assert_warn(rec, "Invalid DOM property `class`. Did you mean `className`?")
    _assert_warn(rec, "    in div")


@pytest.mark.skipif(not is_dev(), reason="nesting validation DEV warnings are DEV-only")
def test_warn_about_class_ssr() -> None:
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        render_to_string(create_element("div", {"class": "muffins"}))
    _assert_warn(rec, "Invalid DOM property `class`. Did you mean `className`?")
    _assert_warn(rec, "    in div")


@pytest.mark.skipif(not is_dev(), reason="nesting validation DEV warnings are DEV-only")
def test_warn_about_incorrect_casing_on_properties_client() -> None:
    c = Container()
    root = create_root(c)
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        root.render(create_element("input", {"type": "text", "tabindex": "1"}))
    _assert_warn(rec, "Invalid DOM property `tabindex`. Did you mean `tabIndex`?")
    _assert_warn(rec, "    in input")


@pytest.mark.skipif(not is_dev(), reason="nesting validation DEV warnings are DEV-only")
def test_warn_about_incorrect_casing_on_properties_ssr() -> None:
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        render_to_string(create_element("input", {"type": "text", "tabindex": "1"}))
    _assert_warn(rec, "Invalid DOM property `tabindex`. Did you mean `tabIndex`?")
    _assert_warn(rec, "    in input")


@pytest.mark.skipif(not is_dev(), reason="nesting validation DEV warnings are DEV-only")
def test_warn_about_incorrect_casing_on_event_handlers_client() -> None:
    c = Container()
    root = create_root(c)
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        root.render(create_element("input", {"type": "text", "oninput": "1"}))
        _assert_warn(rec, "Invalid event handler property `oninput`. Did you mean `onInput`?")
        _assert_warn(rec, "    in input")

        rec.clear()
        root.render(create_element("input", {"type": "text", "onKeydown": "1"}))
        _assert_warn(rec, "Invalid event handler property `onKeydown`. Did you mean `onKeyDown`?")
        _assert_warn(rec, "    in input")


@pytest.mark.skipif(not is_dev(), reason="nesting validation DEV warnings are DEV-only")
def test_warn_about_incorrect_casing_on_event_handlers_ssr() -> None:
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        render_to_string(create_element("input", {"type": "text", "oninput": "1"}))
    _assert_warn(rec, "Invalid event handler property `oninput`.")
    _assert_warn(rec, "for example `onClick`.")
    _assert_warn(rec, "    in input")

    with warnings.catch_warnings(record=True) as rec2:
        warnings.simplefilter("always")
        render_to_string(create_element("input", {"type": "text", "onKeydown": "1"}))
    assert not any("Invalid event handler property" in str(w.message) for w in rec2)


@pytest.mark.skipif(not is_dev(), reason="nesting validation DEV warnings are DEV-only")
def test_warn_about_incorrect_casing_on_the_credentialless_property_ssr() -> None:
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        html = render_to_string(create_element("iframe", {"Credentialless": True}))
    _assert_warn(rec, "Invalid DOM property `Credentialless`. Did you mean `credentialless`?")
    _assert_warn(rec, "    in iframe")
    assert "credentialless" in html
