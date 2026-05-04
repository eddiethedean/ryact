from __future__ import annotations

from typing import Any

from ryact import create_element
from ryact.concurrent import fragment
from ryact_testkit import create_noop_root


def _text(v: str) -> Any:
    return create_element("div", {"text": v})


def test_fragment_keyed_reorder_preserves_children_identity_smoke() -> None:
    # Minimal acceptance slice: keyed siblings in a fragment can reorder without crashing,
    # and the resulting host snapshot matches the new order.
    root = create_noop_root()
    root.render(
        create_element(
            "__fragment__",
            {"children": (create_element("div", {"text": "A", "key": "a"}), create_element("div", {"text": "B", "key": "b"}))},
        )
    )
    root.flush()
    snap = root.get_children_snapshot()
    # Noop snapshot may represent top-level fragments as a list of host children.
    if isinstance(snap, list):
        assert [c["props"]["text"] for c in snap] == ["A", "B"]
    else:
        assert snap["type"] == "__fragment__"
        assert [c["props"]["text"] for c in snap["children"]] == ["A", "B"]

    root.render(
        create_element(
            "__fragment__",
            {"children": (create_element("div", {"text": "B", "key": "b"}), create_element("div", {"text": "A", "key": "a"}))},
        )
    )
    root.flush()
    snap2 = root.get_children_snapshot()
    if isinstance(snap2, list):
        assert [c["props"]["text"] for c in snap2] == ["B", "A"]
    else:
        assert [c["props"]["text"] for c in snap2["children"]] == ["B", "A"]

