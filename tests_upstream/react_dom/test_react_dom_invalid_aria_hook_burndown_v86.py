# Translated: ReactDOMInvalidARIAHook-test.js — aria-* props (burndown v86)
from __future__ import annotations

import warnings

import pytest
from ryact import create_element
from ryact.dev import is_dev
from ryact_dom.server import render_to_string


@pytest.mark.skipif(not is_dev(), reason="ARIA hook warnings are DEV-only")
def test_should_allow_valid_aria_props() -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        render_to_string(create_element("div", {"aria-label": "Bumble bees"}))


@pytest.mark.skipif(not is_dev(), reason="ARIA hook warnings are DEV-only")
def test_should_allow_new_aria_1_3_attributes() -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        render_to_string(create_element("div", {"aria-braillelabel": "Braille label text"}))
        render_to_string(
            create_element("div", {"aria-brailleroledescription": "Navigation menu"}),
        )
        render_to_string(create_element("div", {"aria-colindextext": "Column A"}))
        render_to_string(create_element("div", {"aria-rowindextext": "Row 1"}))
        render_to_string(
            create_element(
                "div",
                {
                    "aria-braillelabel": "Braille text",
                    "aria-colindextext": "First column",
                    "aria-rowindextext": "First row",
                },
            ),
        )


@pytest.mark.skipif(not is_dev(), reason="ARIA hook warnings are DEV-only")
def test_should_warn_for_one_invalid_aria_prop() -> None:
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        render_to_string(create_element("div", {"aria-badprop": "maybe"}))
    assert rec
    msg = str(rec[0].message)
    assert "Invalid aria prop" in msg and "aria-badprop" in msg


@pytest.mark.skipif(not is_dev(), reason="ARIA hook warnings are DEV-only")
def test_should_warn_for_many_invalid_aria_props() -> None:
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        render_to_string(
            create_element(
                "div",
                {"aria-badprop": "Very tall trees", "aria-malprop": "Turbulent seas"},
            ),
        )
    assert rec
    msg = str(rec[0].message)
    assert "Invalid aria props" in msg
    assert "aria-badprop" in msg and "aria-malprop" in msg


@pytest.mark.skipif(not is_dev(), reason="ARIA hook warnings are DEV-only")
def test_should_warn_for_an_improperly_cased_aria_prop() -> None:
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        render_to_string(create_element("div", {"aria-hasPopup": "true"}))
    assert rec
    msg = str(rec[0].message)
    assert "Unknown ARIA attribute" in msg and "aria-haspopup" in msg.lower()


@pytest.mark.skipif(not is_dev(), reason="ARIA hook warnings are DEV-only")
def test_should_warn_for_use_of_recognized_camel_case_aria_attributes() -> None:
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        render_to_string(create_element("div", {"ariaHasPopup": "true"}))
    assert rec
    msg = str(rec[0].message)
    assert "Invalid ARIA attribute `ariaHasPopup`" in msg or "ariaHasPopup" in msg


@pytest.mark.skipif(not is_dev(), reason="ARIA hook warnings are DEV-only")
def test_should_warn_for_use_of_unrecognized_camel_case_aria_attributes() -> None:
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        render_to_string(create_element("div", {"ariaSomethingInvalid": "true"}))
    assert rec
    msg = str(rec[0].message)
    assert "aria-*" in msg or "lowercase" in msg
