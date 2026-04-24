from __future__ import annotations

from ryact import create_element
from ryact_testkit import create_noop_root


def _li(key: str, value: str) -> object:
    return create_element("li", {"key": key, "value": value})


def test_keyed_reorder_emits_move_ops() -> None:
    # Upstream (loosely): ReactChildren/clone/keyed behaviors. Here we assert noop-host ops.
    root = create_noop_root()
    root.render(create_element("ul", None, _li("a", "A"), _li("b", "B"), _li("c", "C")))
    root.clear_ops()

    root.render(create_element("ul", None, _li("c", "C"), _li("a", "A"), _li("b", "B")))
    ops = root.get_ops()

    assert any(op["op"] == "move" for op in ops)
    assert not any(op["op"] == "delete" for op in ops)


def test_keyed_delete_and_insert_emit_ops() -> None:
    root = create_noop_root()
    root.render(create_element("ul", None, _li("a", "A"), _li("b", "B"), _li("c", "C")))
    root.clear_ops()

    root.render(create_element("ul", None, _li("b", "B"), _li("d", "D")))
    ops = root.get_ops()

    assert any(op["op"] == "delete" for op in ops)
    assert any(op["op"] == "insert" for op in ops)
