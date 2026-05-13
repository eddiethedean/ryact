# Translated: DOMPropertyOperations-test.js — custom ``foo`` booleans + ``popoverTarget`` (burndown v109)
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


def test_custom_element_unknown_foo_keeps_boolean_property_semantics() -> None:
    # Upstream: ``values should not be converted to booleans when assigning into custom elements``
    c = Container()
    root = create_root(c)
    root.render(create_element("my-custom-element", {"foo": True}))
    h = c.root.children[0]
    assert isinstance(h, ElementNode)
    assert h.props.get("foo") is True

    root.render(create_element("my-custom-element", {"foo": "bar"}))
    assert h.props.get("foo") == "bar"

    root.render(create_element("my-custom-element", {"foo": False}))
    assert h.props.get("foo") is False

    root.render(create_element("my-custom-element", {"foo": "bar"}))
    assert h.props.get("foo") == "bar"

    root.render(create_element("my-custom-element", {"foo": True}))
    assert h.props.get("foo") is True

    root.render(create_element("my-custom-element", {"foo": None}))
    assert "foo" not in h.props

    root.render(create_element("my-custom-element", {"foo": False}))
    assert h.props.get("foo") is False

    root.render(create_element("my-custom-element", {"foo": None}))
    assert "foo" not in h.props


def test_popover_target_non_string_stripped_from_markup() -> None:
    target = ElementNode(tag="div")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        html = render_to_string(create_element("button", {"type": "button", "popoverTarget": target}))
    assert "popoverTarget" not in html
    assert "popovertarget" not in html.lower()


@pytest.mark.skipif(not is_dev(), reason="popoverTarget invalid-type warning is DEV-only")
def test_popover_target_element_warns_once_per_target_in_dev() -> None:
    target = ElementNode(tag="div")
    c = Container()
    root = create_root(c)
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        root.render(create_element("button", {"type": "button", "popoverTarget": target}))
        root.render(create_element("button", {"type": "button", "popoverTarget": target}))
    pop = [w for w in rec if "popoverTarget` prop" in str(w.message)]
    assert len(pop) == 1
    assert "ElementNode" in str(pop[0].message)
    host = c.root.children[0]
    assert isinstance(host, ElementNode)
    assert "popoverTarget" not in host.props
