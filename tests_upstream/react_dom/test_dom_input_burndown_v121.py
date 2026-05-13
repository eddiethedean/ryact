"""ReactDOMInput-test.js parity: controlled ``null`` / ``undefined`` (v121)."""

from __future__ import annotations

import warnings

from ryact import create_element
from ryact.dev import is_dev
from ryact_dom.dom import Container, ElementNode
from ryact_dom.root import create_root


def _noop(_e: object) -> None:
    return None


def test_setting_controlled_input_to_null_preserves_value_property_937aa64c() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("input", {"type": "text", "value": "first", "onChange": _noop}))
    r.render(create_element("input", {"type": "text", "value": "latest", "onChange": _noop}))
    if is_dev():
        with warnings.catch_warnings(record=True) as rec:
            warnings.simplefilter("always")
            r.render(create_element("input", {"type": "text", "value": None, "onChange": _noop}))
        msgs = [str(w.message) for w in rec]
        assert any("should not be null" in m for m in msgs)
        assert any("changing a controlled input to be uncontrolled" in m for m in msgs)
    else:
        r.render(create_element("input", {"type": "text", "value": None, "onChange": _noop}))
    host = c.root.children[0]
    assert isinstance(host, ElementNode)
    assert host.dom_input_value() == "latest"


def test_setting_controlled_input_to_null_reverts_value_attribute_273e0916() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("input", {"type": "text", "value": "first", "onChange": _noop}))
    r.render(create_element("input", {"type": "text", "value": "latest", "onChange": _noop}))
    host = c.root.children[0]
    assert isinstance(host, ElementNode)
    host.pin_dom_attribute_value("value", "latest")
    if is_dev():
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            r.render(create_element("input", {"type": "text", "value": None, "onChange": _noop}))
    else:
        r.render(create_element("input", {"type": "text", "value": None, "onChange": _noop}))
    assert host.get_attribute("value") == "latest"


def test_setting_controlled_input_to_undefined_preserves_value_property_1fbe75fa() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("input", {"type": "text", "value": "first", "onChange": _noop}))
    r.render(create_element("input", {"type": "text", "value": "latest", "onChange": _noop}))
    if is_dev():
        with warnings.catch_warnings(record=True) as rec:
            warnings.simplefilter("always")
            r.render(create_element("input", {"type": "text", "onChange": _noop}))
        msgs = [str(w.message) for w in rec]
        assert any("changing a controlled input to be uncontrolled" in m for m in msgs)
        assert not any("should not be null" in m for m in msgs)
    else:
        r.render(create_element("input", {"type": "text", "onChange": _noop}))
    host = c.root.children[0]
    assert isinstance(host, ElementNode)
    assert host.dom_input_value() == "latest"


def test_setting_controlled_input_to_undefined_reverts_value_attribute_740ef1d5() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("input", {"type": "text", "value": "first", "onChange": _noop}))
    r.render(create_element("input", {"type": "text", "value": "latest", "onChange": _noop}))
    host = c.root.children[0]
    assert isinstance(host, ElementNode)
    host.pin_dom_attribute_value("value", "latest")
    if is_dev():
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            r.render(create_element("input", {"type": "text", "onChange": _noop}))
    else:
        r.render(create_element("input", {"type": "text", "onChange": _noop}))
    assert host.get_attribute("value") == "latest"
