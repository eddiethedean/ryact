from __future__ import annotations

from typing import Any

from ryact import create_element, use_state
from ryact_testkit import create_noop_root


def _new_token_factory() -> tuple[dict[str, int], Any]:
    ctr = {"n": 0}

    def new_token() -> str:
        ctr["n"] += 1
        return f"token{ctr['n']}"

    return ctr, new_token


def test_preserves_state_if_implicit_key_slot_switches_from_to_null() -> None:
    # Inventory: ReactTopLevelFragment "preserves state if an implicit key slot switches from/to null"
    # We model "implicit keys" as unkeyed siblings whose identity is position-based.
    _, new_token = _new_token_factory()

    def Child(*, label: str) -> object:
        tok, _ = use_state(new_token)
        return create_element("span", {"children": [f"{label}:{tok}"]})

    def App(*, showB: bool) -> object:
        # Slot 1 toggles between None and an element; slots 0 and 2 should preserve state.
        return [
            create_element(Child, {"label": "A"}),
            create_element(Child, {"label": "B"}) if showB else None,
            create_element(Child, {"label": "C"}),
        ]

    root = create_noop_root()
    root.render(create_element(App, {"showB": False}))
    snap1 = str(root.get_children_snapshot())
    assert "A:token1" in snap1
    assert "C:token2" in snap1

    root.clear_ops()
    root.render(create_element(App, {"showB": True}))
    snap2 = str(root.get_children_snapshot())
    # A and C preserve their mount tokens, while B mounts fresh.
    assert "A:token1" in snap2
    assert "B:token3" in snap2
    assert "C:token2" in snap2

    root.clear_ops()
    root.render(create_element(App, {"showB": False}))
    snap3 = str(root.get_children_snapshot())
    # Toggling back removes B but preserves A/C.
    assert "A:token1" in snap3
    assert "C:token2" in snap3
    assert "B:" not in snap3


def test_should_preserve_state_in_a_reorder() -> None:
    # Inventory: ReactTopLevelFragment "should preserve state in a reorder"
    _, new_token = _new_token_factory()

    def Child(*, label: str) -> object:
        tok, _ = use_state(new_token)
        return create_element("li", {"key": label.lower(), "children": [f"{label}:{tok}"]})

    def App(*, flip: bool) -> object:
        a = create_element(Child, {"key": "a", "label": "A"})
        b = create_element(Child, {"key": "b", "label": "B"})
        c = create_element(Child, {"key": "c", "label": "C"})
        return [c, a, b] if flip else [a, b, c]

    root = create_noop_root()
    root.render(create_element(App, {"flip": False}))
    snap1 = str(root.get_children_snapshot())
    assert "A:token1" in snap1 and "B:token2" in snap1 and "C:token3" in snap1

    root.clear_ops()
    root.render(create_element(App, {"flip": True}))
    snap2 = str(root.get_children_snapshot())
    # Keyed reorder should preserve mounted tokens (no remount).
    assert "A:token1" in snap2 and "B:token2" in snap2 and "C:token3" in snap2


def test_should_preserve_state_when_switching_from_a_single_child() -> None:
    # Inventory: ReactTopLevelFragment "should preserve state when switching from a single child"
    _, new_token = _new_token_factory()

    def Child() -> object:
        tok, _ = use_state(new_token)
        return create_element("span", {"children": [f"X:{tok}"]})

    def App(*, asList: bool) -> object:
        child = create_element(Child, {"key": "x"})
        return [child] if asList else child

    root = create_noop_root()
    root.render(create_element(App, {"asList": False}))
    snap1 = str(root.get_children_snapshot())
    assert "X:token1" in snap1

    root.clear_ops()
    root.render(create_element(App, {"asList": True}))
    ops = root.get_ops()
    snap2 = str(root.get_children_snapshot())
    assert "X:token1" in snap2
    # The child should not be deleted+re-inserted just because it became wrapped in a list.
    assert not any(op["op"] == "delete" for op in ops)
