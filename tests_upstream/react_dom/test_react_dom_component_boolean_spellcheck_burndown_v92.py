# Translated: ReactDOMComponent-test.js — boolean + string boolean attributes (burndown v92)
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


def test_warns_on_ambiguous_string_false_for_boolean_hidden() -> None:
    if not is_dev():
        html = render_to_string(create_element("div", {"hidden": "false"}))
        assert "hidden" in html.lower()
        return
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        html = render_to_string(create_element("div", {"hidden": "false"}))
    assert any("string `false` for the boolean attribute `hidden`" in str(w.message) for w in rec)
    assert any("truthy value" in str(w.message) for w in rec)
    lowered = html.lower()
    assert "hidden" in lowered
    assert 'hidden="false"' not in lowered


def test_warns_on_potentially_ambiguous_string_true_for_boolean_hidden() -> None:
    if not is_dev():
        html = render_to_string(create_element("div", {"hidden": "true"}))
        assert "hidden" in html.lower()
        return
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        html = render_to_string(create_element("div", {"hidden": "true"}))
    assert any("string `true` for the boolean attribute `hidden`" in str(w.message) for w in rec)
    assert any("string \"false\"" in str(w.message) for w in rec)
    lowered = html.lower()
    assert "hidden" in lowered
    assert 'hidden="true"' not in lowered


def test_stringifies_implicit_booleans_spellcheck_allowed_attributes() -> None:
    """Upstream: `<div spellCheck />` is `spellCheck={True}`; stringifies to ``spellcheck=\"true\"``."""
    html = render_to_string(create_element("div", {"spellCheck": True}))
    assert 'spellcheck="true"' in html.lower()


def test_spellcheck_boolean_true_stringifies_for_markup() -> None:
    html = render_to_string(create_element("div", {"spellCheck": True}))
    assert 'spellcheck="true"' in html.lower()


def test_spellcheck_boolean_false_stringifies_for_markup() -> None:
    html = render_to_string(create_element("div", {"spellCheck": False}))
    assert 'spellcheck="false"' in html.lower()


def test_spellcheck_implicit_true_persists_on_incremental_host() -> None:
    c = Container()
    root = create_root(c)
    root.render(create_element("div", {"spellCheck": True}))
    h = c.root.children[0]
    assert isinstance(h, ElementNode)
    assert h.props.get("spellCheck") == "true"
