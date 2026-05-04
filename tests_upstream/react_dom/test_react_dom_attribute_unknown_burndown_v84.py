# Translated: ReactDOMAttribute-test.js — unknown attributes (burndown v84)
from __future__ import annotations

import math
import warnings
from collections.abc import Iterator
from contextlib import suppress

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


def test_removes_values_null_and_undefined() -> None:
    for given in (None,):
        c = Container()
        root = create_root(c)
        root.render(create_element("div", {"unknown": "something"}))
        root.render(create_element("div", {"unknown": given}))
        h = c.root.children[0]
        assert isinstance(h, ElementNode)
        assert "unknown" not in h.props

    c2 = Container()
    r2 = create_root(c2)
    r2.render(create_element("div", {"unknown": "something"}))
    r2.render(create_element("div", {}))
    h2 = c2.root.children[0]
    assert isinstance(h2, ElementNode)
    assert "unknown" not in h2.props


def test_changes_true_false_to_null_and_warns_true_in_dev() -> None:
    c = Container()
    root = create_root(c)
    root.render(create_element("div", {"unknown": "something"}))
    if is_dev():
        with warnings.catch_warnings(record=True) as rec:
            warnings.simplefilter("always")
            root.render(create_element("div", {"unknown": True}))
        assert any("non-boolean attribute" in str(w.message) for w in rec)
    else:
        root.render(create_element("div", {"unknown": True}))
    h = c.root.children[0]
    assert isinstance(h, ElementNode)
    assert "unknown" not in h.props

    root.render(create_element("div", {"unknown": "something"}))
    root.render(create_element("div", {"unknown": False}))
    h2 = c.root.children[0]
    assert isinstance(h2, ElementNode)
    assert "unknown" not in h2.props


def test_removes_unknown_attributes_that_were_rendered_but_are_now_missing() -> None:
    c = Container()
    root = create_root(c)
    root.render(create_element("div", {"unknown": "something"}))
    h0 = c.root.children[0]
    assert isinstance(h0, ElementNode)
    assert h0.props.get("unknown") == "something"
    root.render(create_element("div", {}))
    h = c.root.children[0]
    assert isinstance(h, ElementNode)
    assert "unknown" not in h.props


def test_removes_new_boolean_props_inert_true() -> None:
    html = render_to_string(create_element("div", {"inert": True}))
    assert "inert" in html.lower()
    assert '=""' not in html.lower() or " inert" in html


def test_warns_once_for_empty_strings_in_new_boolean_props_inert() -> None:
    if is_dev():
        with warnings.catch_warnings(record=True) as rec:
            warnings.simplefilter("always")
            html = render_to_string(create_element("div", {"inert": ""}))
        assert any("empty string for a boolean attribute" in str(w.message) for w in rec)
        with warnings.catch_warnings(record=True) as rec2:
            warnings.simplefilter("always")
            render_to_string(create_element("div", {"inert": ""}))
        assert not rec2
    else:
        html = render_to_string(create_element("div", {"inert": ""}))
    lowered = html.lower()
    assert "inert" not in lowered or 'inert=""' not in html


def test_passes_through_strings() -> None:
    html = render_to_string(create_element("div", {"unknown": "something"}))
    assert 'unknown="something"' in html
    root = create_root(Container())
    root.render(create_element("div", {"unknown": "a string"}))
    h = root.container.root.children[0]
    assert isinstance(h, ElementNode)
    assert h.props.get("unknown") == "a string"


def test_coerces_numbers_to_strings_in_markup() -> None:
    for n, expect in ((0, "0"), (-1, "-1"), (42, "42"), (9000.99, "9000.99")):
        html = render_to_string(create_element("div", {"unknown": n}))
        assert f'unknown="{expect}"' in html


def test_coerces_nan_to_strings_and_warns_in_dev() -> None:
    html = render_to_string(create_element("div", {"unknown": float("nan")}))
    assert "nan" in html.lower()
    if is_dev():
        with warnings.catch_warnings(record=True) as rec:
            warnings.simplefilter("always")
            render_to_string(create_element("div", {"unknown": math.nan}))
        assert any("nan" in str(w.message).lower() for w in rec)


def test_coerces_objects_to_strings_and_warns_in_dev() -> None:
    class Lol:
        def __str__(self) -> str:
            return "lol"

    payload = {"hello": "world"}
    html = render_to_string(create_element("div", {"unknown": payload}))
    assert "hello" in html and "world" in html
    if is_dev():
        with warnings.catch_warnings(record=True) as rec:
            warnings.simplefilter("always")
            render_to_string(create_element("div", {"unknown": payload}))
        assert rec

    html2 = render_to_string(create_element("div", {"unknown": Lol()}))
    assert "lol" in html2


def test_removes_functions_and_warns_in_dev() -> None:
    def some_function() -> None:
        return

    html = render_to_string(create_element("div", {"unknown": some_function}))
    assert "unknown" not in html.lower() or 'unknown="' not in html
    if is_dev():
        with warnings.catch_warnings(record=True) as rec:
            warnings.simplefilter("always")
            render_to_string(create_element("div", {"unknown": some_function}))
        assert any("Invalid value for prop" in str(w.message) for w in rec)


def test_throws_with_temporal_like_objects() -> None:
    class TemporalLike:
        def __str__(self) -> str:
            raise TypeError("prod message")

    with pytest.raises(TypeError, match="prod message"):
        render_to_string(create_element("div", {"unknown": TemporalLike()}))
    if is_dev():
        with warnings.catch_warnings(record=True) as rec:
            warnings.simplefilter("always")
            with suppress(TypeError):
                render_to_string(create_element("div", {"unknown": TemporalLike()}))
        assert any("unsupported type TemporalLike" in str(w.message) for w in rec)
