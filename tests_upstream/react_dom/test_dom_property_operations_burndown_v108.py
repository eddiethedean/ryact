# Translated: DOMPropertyOperations-test.js — ``progress`` null + custom element inner props (burndown v108)
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


def test_progress_null_clears_value_attribute() -> None:
    # Upstream: regression for indeterminate ``<progress>`` when ``value`` becomes null.
    assert 'value="30"' in render_to_string(create_element("progress", {"value": 30}))
    bare = render_to_string(create_element("progress", {"value": None}))
    assert "value" not in bare

    c = Container()
    root = create_root(c)
    root.render(create_element("progress", {"value": 30}))
    h = c.root.children[0]
    assert isinstance(h, ElementNode)
    assert h.props.get("value") == 30
    root.render(create_element("progress", {"value": None}))
    assert "value" not in h.props


def test_custom_element_innerhtml_not_serialized() -> None:
    html = render_to_string(create_element("my-custom-element", {"innerHTML": "foo"}))
    assert html == "<my-custom-element></my-custom-element>"

    c = Container()
    root = create_root(c)
    root.render(create_element("my-custom-element", {"innerHTML": "foo"}))
    h = c.root.children[0]
    assert isinstance(h, ElementNode)
    assert "innerHTML" not in h.props
    root.render(create_element("my-custom-element", {"innerHTML": "bar"}))
    assert "innerHTML" not in h.props


def test_custom_element_innertext_not_serialized() -> None:
    html = render_to_string(create_element("my-custom-element", {"innerText": "foo"}))
    assert html == "<my-custom-element></my-custom-element>"


def test_custom_element_textcontent_not_serialized() -> None:
    html = render_to_string(create_element("my-custom-element", {"textContent": "foo"}))
    assert html == "<my-custom-element></my-custom-element>"


@pytest.mark.skipif(not is_dev(), reason="custom-element inner prop strips are DEV-warned")
def test_custom_element_inner_props_emit_dev_warnings() -> None:
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        render_to_string(create_element("my-custom-element", {"innerHTML": "x", "innerText": "y", "textContent": "z"}))
    joined = "\n".join(str(w.message) for w in rec)
    assert "innerHTML" in joined and "innerText" in joined and "textContent" in joined
