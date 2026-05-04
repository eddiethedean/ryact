from __future__ import annotations

from typing import Any

from ryact import create_element, create_react_class
from ryact_testkit import create_noop_root


def _span(text: str) -> Any:
    return create_element("span", {"text": text})


def test_create_react_class_renders_and_initializes_state() -> None:
    def getInitialState(self) -> dict[str, object]:  # noqa: N802
        return {"x": 1}

    def render(self) -> object:
        return _span(str(self.state.get("x")))

    C = create_react_class({"displayName": "C", "getInitialState": getInitialState, "render": render})
    root = create_noop_root()
    root.render(create_element(C))
    root.flush()
    assert root.get_children_snapshot()["props"]["text"] == "1"

