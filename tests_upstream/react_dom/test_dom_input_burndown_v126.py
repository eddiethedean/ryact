"""ReactDOMInput-test.js parity: DEV warns for checked/value + default props (v126)."""

from __future__ import annotations

import warnings

import pytest
from ryact import create_element
from ryact.dev import is_dev
from ryact_dom.dom import Container
from ryact_dom.root import create_root


def _noop(_e: object) -> None:
    return None


@pytest.mark.skipif(not is_dev(), reason="controlled input DEV warnings are DEV-only")
def test_warn_controlled_checkbox_false_missing_onchange_2826c285() -> None:
    c = Container()
    r = create_root(c)
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        r.render(create_element("input", {"type": "checkbox", "checked": False}))
    msgs = [str(w.message) for w in rec]
    assert any("provided a `checked` prop" in m and "without an `onChange` handler" in m for m in msgs)


@pytest.mark.skipif(not is_dev(), reason="controlled input DEV warnings are DEV-only")
def test_warn_checked_and_default_checked_radio_b108ad54() -> None:
    c = Container()
    r = create_root(c)
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        r.render(
            create_element(
                "input",
                {
                    "type": "radio",
                    "checked": True,
                    "defaultChecked": True,
                    "readOnly": True,
                },
            ),
        )
    msgs = [str(w.message) for w in rec]
    assert any("both checked and defaultChecked props" in m for m in msgs)


@pytest.mark.skipif(not is_dev(), reason="controlled input DEV warnings are DEV-only")
def test_warn_value_and_default_value_text_77b5cd26() -> None:
    c = Container()
    r = create_root(c)
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        r.render(
            create_element(
                "input",
                {"type": "text", "value": "foo", "defaultValue": "bar", "readOnly": True},
            ),
        )
    msgs = [str(w.message) for w in rec]
    assert any("both value and defaultValue props" in m for m in msgs)


@pytest.mark.skipif(not is_dev(), reason="controlled input DEV warnings are DEV-only")
def test_checkbox_checked_false_with_onchange_no_checked_readonly_warn() -> None:
    c = Container()
    r = create_root(c)
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        r.render(create_element("input", {"type": "checkbox", "checked": False, "onChange": _noop}))
    msgs = [str(w.message) for w in rec]
    assert not any("provided a `checked` prop" in m for m in msgs)
