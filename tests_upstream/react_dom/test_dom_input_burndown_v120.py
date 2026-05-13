"""ReactDOMInput-test.js parity: controlled value warnings vs onInput / uncontrolled (v120)."""

from __future__ import annotations

import warnings

import pytest
from ryact import create_element
from ryact.dev import is_dev
from ryact.element import UNDEFINED
from ryact_dom.dom import Container, ElementNode
from ryact_dom.root import create_root


def _read_only_value_msgs(rec: list[warnings.WarningMessage]) -> list[str]:
    return [str(w.message) for w in rec if "You provided a `value` prop" in str(w.message)]


@pytest.mark.skipif(not is_dev(), reason="controlled input read-only warning is DEV-only")
def test_should_properly_control_value_even_if_no_event_listener_522d226b() -> None:
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        c = Container()
        r = create_root(c)
        r.render(create_element("input", {"type": "text", "value": "lion"}))
    msgs = _read_only_value_msgs(rec)
    assert len(msgs) >= 1
    host = c.root.children[0]
    assert isinstance(host, ElementNode)
    assert host.dom_input_value() == "lion"
    host.dispatch_event("input")
    assert host.dom_input_value() == "lion"


@pytest.mark.skipif(not is_dev(), reason="controlled input read-only warning is DEV-only")
def test_should_not_warn_with_value_and_oninput_handler_16e8aba6() -> None:
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        c = Container()
        r = create_root(c)
        r.render(create_element("input", {"type": "text", "value": "...", "onInput": lambda _e: None}))
    assert _read_only_value_msgs(rec) == []


def test_should_not_warn_about_missing_onchange_in_uncontrolled_inputs_608224f7() -> None:
    if not is_dev():
        return
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        c = Container()
        r = create_root(c)
        r.render(create_element("input"))
        r.render(create_element("input", {"value": UNDEFINED}))
        r.render(create_element("input", {"type": "text"}))
        r.render(create_element("input", {"type": "text", "value": UNDEFINED}))
        r.render(create_element("input", {"type": "checkbox"}))
        r.render(create_element("input", {"type": "checkbox", "checked": UNDEFINED}))
    assert _read_only_value_msgs(rec) == []
