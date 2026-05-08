# Translated: ReactDOMComponent-test.js — nesting validation, unsupported onFocusIn/onFocusOut (v98)
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


_FOCUS_MSG = (
    "React uses onFocus and onBlur instead of onFocusIn and onFocusOut. "
    "All React events are normalized to bubble, so onFocusIn and onFocusOut "
    "are not needed/supported by React."
)


def _assert_focus_warn(rec: list[warnings.WarningMessage], *, tag: str) -> None:
    assert any(_FOCUS_MSG in str(w.message) for w in rec), [str(w.message) for w in rec]
    assert any(f"    in {tag}" in str(w.message) for w in rec), [str(w.message) for w in rec]


def _noop_event_handler(_e: object = None) -> None:
    return None


@pytest.mark.skipif(not is_dev(), reason="unsupported focus prop warnings are DEV-only")
def test_warns_on_focus_in_and_focus_out_client() -> None:
    c = Container()
    root = create_root(c)
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        root.render(create_element("div", {"onFocusIn": _noop_event_handler}))
        _assert_focus_warn(rec, tag="div")
        node = c.root.children[0]
        assert isinstance(node, ElementNode)
        assert "onFocusIn" not in node.props

        rec.clear()
        root.render(create_element("div", {"onFocusOut": _noop_event_handler}))
        _assert_focus_warn(rec, tag="div")
        node2 = c.root.children[0]
        assert isinstance(node2, ElementNode)
        assert "onFocusOut" not in node2.props


@pytest.mark.skipif(not is_dev(), reason="unsupported focus prop warnings are DEV-only")
def test_warns_on_focus_in_and_focus_out_case_insensitive_client() -> None:
    c = Container()
    root = create_root(c)
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        root.render(create_element("div", {"onfocusin": _noop_event_handler}))
        _assert_focus_warn(rec, tag="div")

        rec.clear()
        root.render(create_element("div", {"onFOCUSOUT": _noop_event_handler}))
        _assert_focus_warn(rec, tag="div")


@pytest.mark.skipif(not is_dev(), reason="unsupported focus prop warnings are DEV-only")
def test_warns_on_focus_in_and_focus_out_ssr() -> None:
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        render_to_string(create_element("div", {"onFocusIn": _noop_event_handler}))
        _assert_focus_warn(rec, tag="div")

        rec.clear()
        render_to_string(create_element("div", {"onFocusOut": _noop_event_handler}))
        _assert_focus_warn(rec, tag="div")


@pytest.mark.skipif(not is_dev(), reason="unsupported focus prop warnings are DEV-only")
def test_warns_on_focus_in_and_focus_out_case_insensitive_ssr() -> None:
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        render_to_string(create_element("div", {"onfocusin": _noop_event_handler}))
        _assert_focus_warn(rec, tag="div")

        rec.clear()
        render_to_string(create_element("div", {"onFOCUSOUT": _noop_event_handler}))
        _assert_focus_warn(rec, tag="div")


def test_pythonic_on_focus_in_stripped_from_markup() -> None:
    html = render_to_string(create_element("div", {"on_focus_in": _noop_event_handler}))
    assert "focusin" not in html.lower()
