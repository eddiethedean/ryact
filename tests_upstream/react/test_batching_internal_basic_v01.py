from __future__ import annotations

from typing import Any

from ryact import create_element
from ryact_testkit import create_noop_root


def _div(text: str) -> Any:
    return create_element("div", {"text": text})


def test_noop_root_batched_updates_smoke() -> None:
    root = create_noop_root()

    def batch() -> None:
        root.render(_div("a"))
        root.render(_div("b"))

    root.batched_updates(batch)
    root.flush()
    assert root.get_children_snapshot()["props"]["text"] in ("a", "b")

