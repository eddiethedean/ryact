from __future__ import annotations

from ryact import create_element, use_state
from ryact_testkit import create_noop_root


def test_should_not_preserve_state_when_switching_to_a_nested_array() -> None:
    # Upstream: ReactTopLevelFragment-test.js
    # "should not preserve state when switching to a nested array"
    ctr = {"n": 0}

    def new_token() -> str:
        ctr["n"] += 1
        return f"token{ctr['n']}"

    def Child(*, label: str) -> object:
        tok, _ = use_state(new_token)
        return create_element("span", {"children": [f"{label}:{tok}"]})

    def App(*, nested: bool) -> object:
        child = create_element(Child, {"key": "x", "label": "X"})
        if nested:
            # Nested array introduces an implicit fragment wrapper.
            return [[child]]
        return [child]

    root = create_noop_root()
    root.render(create_element(App, {"nested": False}))
    snap1 = str(root.get_children_snapshot())
    assert "X:token1" in snap1

    root.render(create_element(App, {"nested": True}))
    snap2 = str(root.get_children_snapshot())
    # Switching shapes should remount the child (state resets).
    assert "X:token2" in snap2
