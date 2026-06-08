"""ReactDOMInput-test.js parity: submit value, defaultValue updates, DEV read-only warns (v124)."""

from __future__ import annotations

import warnings

import pytest
from ryact import create_element
from ryact.dev import is_dev
from ryact_dom.dom import Container, ElementNode
from ryact_dom.root import create_root
from ryact_dom.server import render_to_string


def _read_only_value_warn(msgs: list[str]) -> bool:
    return any("without an `onChange` handler" in m and "read-only" in m and "`value` prop" in m for m in msgs)


def test_set_value_on_submit_input_83c53bb7() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("input", {"type": "submit", "value": "banana"}))
    host = c.root.children[0]
    assert isinstance(host, ElementNode)
    assert host.props.get("value") == "banana"
    html = render_to_string(create_element("input", {"type": "submit", "value": "banana"}))
    assert 'type="submit"' in html and 'value="banana"' in html


def test_update_defaultvalue_to_empty_string_a7e42c45() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("input", {"type": "text", "defaultValue": "foo"}))
    r.render(create_element("input", {"type": "text", "defaultValue": ""}))
    host = c.root.children[0]
    assert isinstance(host, ElementNode)
    assert host.dom_input_value() == ""


def test_update_defaultvalue_for_uncontrolled_input_740a637d() -> None:
    """Ryact-dom refreshes the host value when ``defaultValue`` changes on an uncontrolled input."""

    c = Container()
    r = create_root(c)
    r.render(create_element("input", {"type": "text", "defaultValue": "0"}))
    host = c.root.children[0]
    assert isinstance(host, ElementNode)
    assert host.dom_input_value() == "0"
    r.render(create_element("input", {"type": "text", "defaultValue": "1"}))
    assert host.dom_input_value() == "1"


@pytest.mark.skipif(not is_dev(), reason="read-only controlled warning is DEV-only")
def test_warn_controlled_value_0_missing_onchange_07cba36d() -> None:
    c = Container()
    r = create_root(c)
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        r.render(create_element("input", {"type": "text", "value": 0}))
    assert _read_only_value_warn([str(w.message) for w in rec])


@pytest.mark.skipif(not is_dev(), reason="read-only controlled warning is DEV-only")
def test_warn_controlled_value_string_0_missing_onchange_1cc38102() -> None:
    c = Container()
    r = create_root(c)
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        r.render(create_element("input", {"type": "text", "value": "0"}))
    assert _read_only_value_warn([str(w.message) for w in rec])


@pytest.mark.skipif(not is_dev(), reason="read-only controlled warning is DEV-only")
def test_warn_controlled_value_empty_string_missing_onchange_f1d0662d() -> None:
    c = Container()
    r = create_root(c)
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        r.render(create_element("input", {"type": "text", "value": ""}))
    assert _read_only_value_warn([str(w.message) for w in rec])
