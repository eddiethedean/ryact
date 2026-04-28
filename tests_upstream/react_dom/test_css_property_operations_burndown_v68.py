from __future__ import annotations

import math

from ryact import create_element
from ryact_dom import render_to_string
from ryact_testkit import WarningCapture


def test_should_automatically_append_px_to_relevant_styles() -> None:
    html = render_to_string(create_element("div", {"style": {"width": 5}}))
    assert 'style="width:5px"' in html


def test_should_create_vendor_prefixed_markup_correctly() -> None:
    html = render_to_string(create_element("div", {"style": {"msTransition": "all"}}))
    assert 'style="-ms-transition:all"' in html


def test_should_not_add_units_to_css_custom_properties() -> None:
    html = render_to_string(create_element("div", {"style": {"--foo": 5}}))
    assert 'style="--foo:5"' in html


def test_should_not_append_px_to_styles_that_might_need_a_number() -> None:
    html = render_to_string(create_element("div", {"style": {"opacity": 0.5, "zIndex": 1}}))
    assert 'style="opacity:0.5;z-index:1"' in html or 'style="z-index:1;opacity:0.5"' in html


def test_should_not_hyphenate_custom_css_property() -> None:
    html = render_to_string(create_element("div", {"style": {"--some-custom": "red"}}))
    assert 'style="--some-custom:red"' in html


def test_should_not_set_style_attribute_when_no_styles_exist() -> None:
    html = render_to_string(create_element("div", {"style": {}}))
    assert "<div>" in html and "style=" not in html


def test_should_not_warn_when_setting_css_custom_properties() -> None:
    with WarningCapture() as wc:
        html = render_to_string(create_element("div", {"style": {"--foo": "bar"}}))
    assert 'style="--foo:bar"' in html
    assert wc.messages == []


def test_should_set_style_attribute_when_styles_exist() -> None:
    html = render_to_string(create_element("div", {"style": {"color": "red"}}))
    assert 'style="color:red"' in html


def test_should_trim_values() -> None:
    html = render_to_string(create_element("div", {"style": {"color": "  red  "}}))
    assert 'style="color:red"' in html


def test_should_warn_about_style_containing_a_nan_value() -> None:
    with WarningCapture() as wc:
        _ = render_to_string(create_element("div", {"style": {"width": float("nan")}}))
    assert wc.messages


def test_should_warn_about_style_containing_an_infinity_value() -> None:
    with WarningCapture() as wc:
        _ = render_to_string(create_element("div", {"style": {"width": math.inf}}))
    assert wc.messages


def test_should_warn_about_style_having_a_trailing_semicolon() -> None:
    with WarningCapture() as wc:
        html = render_to_string(create_element("div", {"style": {"color": "red;"}}))
    assert 'style="color:red"' in html
    assert wc.messages


def test_should_warn_when_using_hyphenated_style_names() -> None:
    with WarningCapture() as wc:
        html = render_to_string(create_element("div", {"style": {"background-color": "red"}}))
    assert "background-color:red" in html
    assert wc.messages


def test_should_warn_when_updating_hyphenated_style_names() -> None:
    with WarningCapture() as wc1:
        _ = render_to_string(create_element("div", {"style": {"background-color": "red"}}))
    with WarningCapture() as wc2:
        _ = render_to_string(create_element("div", {"style": {"background-color": "blue"}}))
    assert wc1.messages and wc2.messages


def test_warns_when_miscapitalizing_vendored_style_names() -> None:
    with WarningCapture() as wc:
        html = render_to_string(create_element("div", {"style": {"webkitTransform": "none"}}))
    assert "-webkit-transform:none" in html
    assert wc.messages

