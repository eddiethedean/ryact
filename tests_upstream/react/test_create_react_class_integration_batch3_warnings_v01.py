from __future__ import annotations

from typing import Any

from ryact.create_react_class import create_react_class
from ryact_testkit import WarningCapture


def test_warn_on_invalid_prop_types() -> None:
    with WarningCapture() as wc:
        _ = create_react_class({"render": lambda self: None, "propTypes": 123})
    wc.assert_any("Invalid propTypes")


def test_warn_on_invalid_context_types() -> None:
    with WarningCapture() as wc:
        _ = create_react_class({"render": lambda self: None, "contextTypes": 123})
    wc.assert_any("Invalid contextTypes")


def test_warn_when_misspelling_componentwillreceiveprops() -> None:
    with WarningCapture() as wc:
        _ = create_react_class({"render": lambda self: None, "componentWillRecieveProps": lambda self, p: None})
    wc.assert_any("componentWillReceiveProps")


def test_warn_when_misspelling_unsafe_componentwillreceiveprops() -> None:
    with WarningCapture() as wc:
        _ = create_react_class({"render": lambda self: None, "UNSAFE_componentWillRecieveProps": lambda self, p: None})
    wc.assert_any("UNSAFE_componentWillReceiveProps")


def test_warn_when_misspelling_shouldcomponentupdate() -> None:
    with WarningCapture() as wc:
        _ = create_react_class({"render": lambda self: None, "shouldComponentUpdat": lambda self, p, s: True})
    wc.assert_any("shouldComponentUpdate")


def test_warn_when_using_mixins() -> None:
    with WarningCapture() as wc:
        _ = create_react_class({"render": lambda self: None, "mixins": [object()]})
    wc.assert_any("mixins")

