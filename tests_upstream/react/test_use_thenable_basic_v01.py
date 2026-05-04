from __future__ import annotations

from typing import Any

from ryact import create_element, use
from ryact.concurrent import Thenable
from ryact_testkit import create_noop_root


def _span(text: str) -> Any:
    return create_element("span", {"text": text})


def test_use_thenable_fulfilled_value() -> None:
    t = Thenable()
    t.resolve("Hi")

    def App() -> Any:
        v = use(t)
        return _span(str(v))

    root = create_noop_root()
    root.render(create_element(App))
    root.flush()
    assert root.get_children_snapshot()["props"]["text"] == "Hi"

