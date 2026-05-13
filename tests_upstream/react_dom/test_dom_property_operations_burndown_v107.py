# Translated: DOMPropertyOperations-test.js — iframe ``credentialless`` (burndown v107)
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


def test_iframe_credentialless_boolean_ssr_and_incremental() -> None:
    # Upstream: ``<iframe credentialless />`` toggles minimized attribute on/off.
    assert render_to_string(create_element("iframe", {"credentialless": True})) == "<iframe credentialless></iframe>"
    assert render_to_string(create_element("iframe", {"credentialless": False})) == "<iframe></iframe>"

    c = Container()
    root = create_root(c)
    root.render(create_element("iframe", {"credentialless": True}))
    h = c.root.children[0]
    assert isinstance(h, ElementNode)
    assert h.props.get("credentialless") is True

    root.render(create_element("iframe", {"credentialless": False}))
    assert "credentialless" not in h.props


def test_iframe_credentialless_string_true_warns_in_dev() -> None:
    # Upstream: string ``credentialless="true"`` warns (console error in Jest) and still sets presence.
    if not is_dev():
        html = render_to_string(create_element("iframe", {"credentialless": "true"}))
        assert "credentialless" in html.lower()
        return

    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        html = render_to_string(create_element("iframe", {"credentialless": "true"}))
    assert any("string `true` for the boolean attribute `credentialless`" in str(w.message) for w in rec)
    assert "<iframe credentialless>" in html
