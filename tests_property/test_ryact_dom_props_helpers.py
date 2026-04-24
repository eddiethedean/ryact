from __future__ import annotations

from typing import Any

from ryact_dom.props import cx, on, style, style_dict


def test_cx_joins_truthy_fragments() -> None:
    assert cx(None, "a", False, "b", "", "  ", 0) == "a b 0"


def test_on_builds_pythonic_event_prop() -> None:
    def handler(*_: Any) -> None:
        return

    assert on("click", handler) == {"on_click": handler}
    assert on("key-down", handler) == {"on_key_down": handler}


def test_style_helpers_return_dicts() -> None:
    assert style(color="red") == {"color": "red"}
    assert style_dict({"x": 1}) == {"x": 1}
