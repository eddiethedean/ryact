# Translated: ReactDOMComponent-test.js — attribute name safety + intrinsic casing (burndown v87)
from __future__ import annotations

import warnings

import pytest
from ryact import create_element
from ryact.dev import is_dev
from ryact_dom.dom import Container, ElementNode
from ryact_dom.root import create_root
from ryact_dom.server import render_to_string

_K_INJECTION_QUOTE = 'blah" onclick="beevil" noise="hi'
_K_INJECTION_CLOSE = '></div><script>alert("hi")</script>'
_K_CUSTOM_CLOSE = '></x-foo-component><script>alert("hi")</script>'


@pytest.mark.skipif(not is_dev(), reason="invalid attribute warnings are DEV-only")
def test_should_reject_attribute_key_injection_attack_on_markup_for_regular_dom_ssr() -> None:
    for _ in range(3):
        el1 = create_element("div", {_K_INJECTION_QUOTE: "selected"})
        el2 = create_element("div", {_K_INJECTION_CLOSE: "selected"})
        with warnings.catch_warnings(record=True) as rec:
            warnings.simplefilter("always")
            result1 = render_to_string(el1)
            result2 = render_to_string(el2)
        assert rec and "Invalid attribute name" in str(rec[0].message)
        assert rec and "Invalid attribute name" in str(rec[1].message)
        assert "onclick" not in result1.lower()
        assert "script" not in result2.lower()


@pytest.mark.skipif(not is_dev(), reason="invalid attribute warnings are DEV-only")
def test_should_reject_attribute_key_injection_attack_on_markup_for_custom_elements_ssr() -> None:
    for _ in range(3):
        el1 = create_element("x-foo-component", {_K_INJECTION_QUOTE: "selected"})
        el2 = create_element("x-foo-component", {_K_CUSTOM_CLOSE: "selected"})
        with warnings.catch_warnings(record=True) as rec:
            warnings.simplefilter("always")
            result1 = render_to_string(el1)
            result2 = render_to_string(el2)
        assert len(rec) >= 2
        assert "onclick" not in result1.lower()
        assert "script" not in result2.lower()


@pytest.mark.skipif(not is_dev(), reason="invalid attribute warnings are DEV-only")
def test_should_reject_attribute_key_injection_attack_on_mount_for_regular_dom() -> None:
    for _ in range(3):
        c = Container()
        root = create_root(c)
        root.render(create_element("div", {_K_INJECTION_QUOTE: "selected"}))
        host = c.root.children[0]
        assert isinstance(host, ElementNode)
        assert len(host.props) == 0

        root.render(create_element("div", {_K_INJECTION_CLOSE: "selected"}))
        host2 = c.root.children[0]
        assert isinstance(host2, ElementNode)
        assert len(host2.props) == 0


@pytest.mark.skipif(not is_dev(), reason="invalid attribute warnings are DEV-only")
def test_should_reject_attribute_key_injection_attack_on_mount_for_custom_elements() -> None:
    for _ in range(3):
        c = Container()
        root = create_root(c)
        root.render(create_element("x-foo-component", {_K_INJECTION_QUOTE: "selected"}))
        host = c.root.children[0]
        assert isinstance(host, ElementNode)
        assert len(host.props) == 0

        root.render(create_element("x-foo-component", {_K_CUSTOM_CLOSE: "selected"}))
        host2 = c.root.children[0]
        assert isinstance(host2, ElementNode)
        assert len(host2.props) == 0


@pytest.mark.skipif(not is_dev(), reason="invalid attribute warnings are DEV-only")
def test_should_reject_attribute_key_injection_attack_on_update_for_regular_dom() -> None:
    for _ in range(3):
        c = Container()
        root = create_root(c)
        root.render(create_element("div", {}))
        root.render(create_element("div", {_K_INJECTION_QUOTE: "selected"}))
        assert len(c.root.children[0].props) == 0  # type: ignore[index]
        root.render(create_element("div", {_K_INJECTION_CLOSE: "selected"}))
        assert len(c.root.children[0].props) == 0  # type: ignore[index]


@pytest.mark.skipif(not is_dev(), reason="invalid attribute warnings are DEV-only")
def test_should_reject_attribute_key_injection_attack_on_update_for_custom_elements() -> None:
    for _ in range(3):
        c = Container()
        root = create_root(c)
        root.render(create_element("x-foo-component", {}))
        root.render(create_element("x-foo-component", {_K_INJECTION_QUOTE: "selected"}))
        assert len(c.root.children[0].props) == 0  # type: ignore[index]
        root.render(create_element("x-foo-component", {_K_CUSTOM_CLOSE: "selected"}))
        assert len(c.root.children[0].props) == 0  # type: ignore[index]


@pytest.mark.skipif(not is_dev(), reason="intrinsic casing warning is DEV-only")
def test_should_warn_on_upper_case_html_tags_not_svg_nor_custom_tags() -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        c = Container()
        create_root(c).render(create_element("svg", None, create_element("PATH")))
        c2 = Container()
        create_root(c2).render(create_element("CUSTOM-TAG"))

    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        c3 = Container()
        create_root(c3).render(create_element("IMG"))
    assert rec
    msg = str(rec[0].message).lower()
    assert "incorrect casing" in msg and "img" in msg
