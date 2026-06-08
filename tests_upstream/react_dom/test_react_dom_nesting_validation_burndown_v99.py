# Translated: ReactDOMComponent-test.js / validateDOMNesting-test.js — HTML nesting DEV validation (v99)
from __future__ import annotations

import warnings
from collections.abc import Iterator

import pytest
from ryact import Component, create_element
from ryact.dev import is_dev
from ryact_dom.dom import Container
from ryact_dom.html_props import reset_dom_warning_state
from ryact_dom.root import create_root
from ryact_dom.server import render_to_string
from ryact_dom.validate_dom_nesting import reset_validate_dom_nesting_dev_state


@pytest.fixture(autouse=True)
def _reset_warning_state() -> Iterator[None]:
    reset_dom_warning_state()
    reset_validate_dom_nesting_dev_state()
    yield


def _nesting_warnings(rec: list[warnings.WarningMessage]) -> list[str]:
    out: list[str] = []
    for w in rec:
        m = str(w.message)
        if "cannot be a child of <" in m or "cannot be a descendant of <" in m:
            out.append(m)
        if "text nodes cannot be a child of" in m:
            out.append(m)
        if "whitespace text nodes cannot be a child of" in m:
            out.append(m)
        if "cannot contain a nested <" in m:
            out.append(m)
    return out


@pytest.mark.skipif(not is_dev(), reason="DOM nesting validation is DEV-only")
def test_warns_on_invalid_nesting_tr_in_div() -> None:
    c = Container()
    root = create_root(c)
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        root.render(
            create_element(
                "div",
                None,
                create_element("tr", None),
                create_element("tr", None),
            ),
        )
    nw = _nesting_warnings(rec)
    assert any("In HTML, <tr> cannot be a child of <div>" in m for m in nw), nw
    assert any("hydration error" in m.lower() for m in nw)


@pytest.mark.skipif(not is_dev(), reason="DOM nesting validation is DEV-only")
def test_warns_on_invalid_nesting_at_root_mount_p() -> None:
    c = Container(dom_nesting_mount_tag="p")
    root = create_root(c)
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        root.render(create_element("span", None, create_element("p", None)))
    nw = _nesting_warnings(rec)
    assert any("In HTML, <p> cannot be a descendant of <p>" in m for m in nw), nw


class _Row(Component):
    def render(self):
        return create_element("tr", None, "x")


class _Foo(Component):
    def render(self):
        return create_element("table", None, create_element(_Row, None), " ")


@pytest.mark.skipif(not is_dev(), reason="DOM nesting validation is DEV-only")
def test_warns_nicely_for_table_rows() -> None:
    c = Container()
    root = create_root(c)
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        root.render(create_element(_Foo, None))
    nw = _nesting_warnings(rec)
    assert any("In HTML, <tr> cannot be a child of <table>" in m and "tbody" in m.lower() for m in nw), nw
    assert any("cannot contain a nested <tr>" in m for m in nw), nw
    assert any("text nodes cannot be a child of <tr>" in m for m in nw), nw
    assert any("whitespace text nodes cannot be a child of <table>" in m for m in nw), nw


def _Row_fn(props=None, **kw):
    p = dict(props or {})
    p.update(kw)
    return create_element("tr", None, p.get("children", ()))


def _Foo_fn(props=None, **kw):
    p = dict(props or {})
    p.update(kw)
    return create_element("table", None, p.get("children", ()))


@pytest.mark.skipif(not is_dev(), reason="DOM nesting validation is DEV-only")
def test_warns_nicely_for_updating_table_rows_to_use_text() -> None:
    c = Container()
    root = create_root(c)
    root.render(create_element(_Foo_fn, None))

    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        root.render(create_element(_Foo_fn, None, " "))
    nw = _nesting_warnings(rec)
    assert any("whitespace text nodes cannot be a child of <table>" in m for m in nw), nw

    reset_validate_dom_nesting_dev_state()
    with warnings.catch_warnings(record=True) as rec2:
        warnings.simplefilter("always")
        root.render(
            create_element(
                _Foo_fn,
                None,
                create_element(
                    "tbody",
                    None,
                    create_element(_Row_fn, None),
                ),
            ),
        )
    assert not _nesting_warnings(rec2)

    reset_validate_dom_nesting_dev_state()
    with warnings.catch_warnings(record=True) as rec3:
        warnings.simplefilter("always")
        root.render(
            create_element(
                _Foo_fn,
                None,
                create_element(
                    "tbody",
                    None,
                    create_element(_Row_fn, None, "text"),
                ),
            ),
        )
    nw3 = _nesting_warnings(rec3)
    assert any("text nodes cannot be a child of <tr>" in m for m in nw3), nw3


@pytest.mark.skipif(not is_dev(), reason="DOM nesting validation is DEV-only")
def test_valid_dom_nesting_no_false_positives_table_chain() -> None:
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        render_to_string(
            create_element(
                "table",
                None,
                create_element(
                    "tbody", None, create_element("tr", None, create_element("td", None, create_element("b", None)))
                ),
            ),
        )
    assert not _nesting_warnings(rec)


@pytest.mark.skipif(not is_dev(), reason="DOM nesting validation is DEV-only")
def test_problematic_nesting_p_in_p() -> None:
    c = Container()
    root = create_root(c)
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        root.render(create_element("p", None, create_element("p", None)))
    nw = _nesting_warnings(rec)
    assert any("cannot be a descendant of <p>" in m for m in nw), nw


@pytest.mark.skipif(not is_dev(), reason="DOM nesting validation is DEV-only")
def test_problematic_nesting_table_tr_direct() -> None:
    c = Container()
    root = create_root(c)
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        root.render(create_element("table", None, create_element("tr", None)))
    nw = _nesting_warnings(rec)
    assert any("<tr> cannot be a child of <table>" in m for m in nw), nw


@pytest.mark.skipif(not is_dev(), reason="DOM nesting validation is DEV-only")
def test_implicit_root_allows_div_under_document() -> None:
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        render_to_string(create_element("div", None, create_element("meta")))
    assert not _nesting_warnings(rec)


@pytest.mark.skipif(not is_dev(), reason="DOM nesting validation is DEV-only")
def test_implicit_root_allows_body_like_content() -> None:
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        render_to_string(create_element("div", None, create_element("p", None, "hello")))
    assert not _nesting_warnings(rec)


@pytest.mark.skipif(not is_dev(), reason="DOM nesting validation is DEV-only")
def test_ssr_warns_on_invalid_nesting_tr_in_div() -> None:
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        render_to_string(
            create_element(
                "div",
                None,
                create_element("tr", None),
                create_element("tr", None),
            ),
        )
    nw = _nesting_warnings(rec)
    assert any("In HTML, <tr> cannot be a child of <div>" in m for m in nw), nw


@pytest.mark.skipif(not is_dev(), reason="DOM nesting validation is DEV-only")
def test_ssr_warns_on_invalid_nesting_at_singleton_mount_p() -> None:
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        render_to_string(
            create_element("span", None, create_element("p", None)),
            dom_nesting_mount_tag="p",
        )
    nw = _nesting_warnings(rec)
    assert any("In HTML, <p> cannot be a descendant of <p>" in m for m in nw), nw


@pytest.mark.skipif(not is_dev(), reason="DOM nesting validation is DEV-only")
def test_ssr_warns_nicely_for_table_rows_fn_components() -> None:
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        render_to_string(
            create_element(_Foo_fn, None, create_element(_Row_fn, None, "x"), " "),
        )
    nw = _nesting_warnings(rec)
    assert any("In HTML, <tr> cannot be a child of <table>" in m and "tbody" in m.lower() for m in nw), nw
    assert any("cannot contain a nested <tr>" in m for m in nw), nw
    assert any("text nodes cannot be a child of <tr>" in m for m in nw), nw
    assert any("whitespace text nodes cannot be a child of <table>" in m for m in nw), nw
