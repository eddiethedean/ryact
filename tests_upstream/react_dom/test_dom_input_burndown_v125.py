"""ReactDOMInput-test.js parity: controlled→uncontrolled DEV warns; date defaultValue (v125)."""

from __future__ import annotations

import warnings

import pytest
from ryact import create_element
from ryact.dev import is_dev
from ryact_dom.dom import Container, ElementNode
from ryact_dom.root import create_root


def _noop(_e: object) -> None:
    return None


def _controlled_to_uncontrolled_msgs(msgs: list[str]) -> list[str]:
    return [m for m in msgs if "changing a controlled input to be uncontrolled" in m]


def _null_value_warn(msgs: list[str]) -> bool:
    return any("`value` prop on `input` should not be null" in m for m in msgs)


@pytest.mark.skipif(not is_dev(), reason="controlled/uncontrolled warnings are DEV-only")
def test_warn_controlled_input_switches_to_uncontrolled_value_undefined_fa9025dd() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("input", {"type": "text", "value": "controlled", "onChange": _noop}))
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        r.render(create_element("input", {"type": "text"}))
    msgs = [str(w.message) for w in rec]
    assert _controlled_to_uncontrolled_msgs(msgs)


@pytest.mark.skipif(not is_dev(), reason="controlled/uncontrolled + null value warnings are DEV-only")
def test_warn_controlled_input_switches_to_uncontrolled_value_null_e741b334() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("input", {"type": "text", "value": "controlled", "onChange": _noop}))
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        r.render(create_element("input", {"type": "text", "value": None}))
    msgs = [str(w.message) for w in rec]
    assert _null_value_warn(msgs)
    assert _controlled_to_uncontrolled_msgs(msgs)


def test_update_defaultvalue_for_uncontrolled_date_input_56d6c505() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("input", {"type": "date", "defaultValue": "1980-01-01"}))
    host = c.root.children[0]
    assert isinstance(host, ElementNode)
    assert host.dom_input_value() == "1980-01-01"
    r.render(create_element("input", {"type": "date", "defaultValue": "2000-01-01"}))
    assert host.dom_input_value() == "2000-01-01"


@pytest.mark.skipif(not is_dev(), reason="defaultValue null coercions are DEV-only")
def test_treat_defaultvalue_null_as_missing_65180b4b() -> None:
    """``defaultValue={None}`` warns and keeps the prior host value (merge path)."""

    c = Container()
    r = create_root(c)
    r.render(create_element("input", {"type": "text", "defaultValue": "0"}))
    host = c.root.children[0]
    assert isinstance(host, ElementNode)
    assert host.dom_input_value() == "0"
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        r.render(create_element("input", {"type": "text", "defaultValue": None}))
    msgs = [str(w.message) for w in rec]
    assert _null_value_warn(msgs)
    assert _controlled_to_uncontrolled_msgs(msgs)
    assert host.dom_input_value() == "0"
