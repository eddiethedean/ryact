# Translated: ReactDOMComponent-test.js — intrinsic host DEV nudges + DSH Temporal-like (burndown v96)
from __future__ import annotations

import warnings
from collections.abc import Iterator

import pytest
from ryact import Component, create_element
from ryact.dev import is_dev
from ryact_dom.dom import Container, ElementNode
from ryact_dom.html_props import reset_dom_warning_state
from ryact_dom.intrinsic_tag_dev import reset_intrinsic_tag_dev_warning_state
from ryact_dom.root import create_root
from ryact_dom.server import render_to_string


@pytest.fixture(autouse=True)
def _reset_warning_dedupe() -> Iterator[None]:
    reset_dom_warning_state()
    reset_intrinsic_tag_dev_warning_state()
    yield


class _UpperVoidHost(Component):
    def render(self):
        return create_element("BR", None)


def test_mis_cased_void_br_emits_closing_pair_ssr() -> None:
    html = render_to_string(create_element(_UpperVoidHost, {}))
    assert "</BR>" in html


@pytest.mark.skipif(not is_dev(), reason="intrinsic DEV warnings are DEV-only")
def test_warns_uppercase_self_closing_void_tag_casing_stack_ssr() -> None:
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        render_to_string(create_element(_UpperVoidHost, {}))
    assert any("<BR /> is using incorrect casing" in str(w.message) for w in rec)
    assert any("in BR" in str(w.message) for w in rec)


@pytest.mark.skipif(not is_dev(), reason="reserved aria warning is DEV-only")
def test_warns_reserved_aria_prop_and_omits_from_markup() -> None:
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        html = render_to_string(create_element("div", {"aria": "hello"}))
    assert any("The `aria` attribute is reserved for future use in React" in str(w.message) for w in rec)
    assert any("    in div" in str(w.message) for w in rec)
    assert "aria=" not in html.lower()


@pytest.mark.skipif(not is_dev(), reason="unrecognized tag warning is DEV-only")
def test_warns_unrecognized_lowercase_intrinsic_tag() -> None:
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        render_to_string(create_element("bar", {}))
    assert any("The tag <bar> is unrecognized in this browser" in str(w.message) for w in rec)


@pytest.mark.skipif(not is_dev(), reason="unrecognized tag warning is DEV-only")
def test_dedupes_unrecognized_tag_warning_for_same_tag() -> None:
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        render_to_string(create_element("foo", {}))
        render_to_string(create_element("foo", {}))
    assert sum("The tag <foo> is unrecognized" in str(w.message) for w in rec) == 1


@pytest.mark.skipif(not is_dev(), reason="unrecognized tag warning is DEV-only")
def test_known_time_element_does_not_warn_unrecognized() -> None:
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        render_to_string(create_element("time", {"dateTime": "2020"}, "x"))
    assert not any("is unrecognized in this browser" in str(w.message) for w in rec)


class _TemporalLikeHtml:
    def __str__(self) -> str:
        return "2020-01-01"


def test_dangerously_inner_html_accepts_temporal_like_via_str_coercion_host() -> None:
    c = Container()
    root = create_root(c)
    root.render(
        create_element("div", {"dangerouslySetInnerHTML": {"__html": _TemporalLikeHtml()}}),
    )
    div = c.root.children[0]
    assert isinstance(div, ElementNode)
    assert div.innerHTML == "2020-01-01"


class _Animal(Component):
    def render(self):
        return create_element("div", {"style": 1})


def test_nested_class_component_invalid_style_throws_like_update_component_report() -> None:
    with pytest.raises(ValueError, match=r"The `style` prop expects a mapping"):
        render_to_string(create_element(_Animal, {}))
