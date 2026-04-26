from __future__ import annotations

from typing import Any

from ryact import create_element
from ryact.concurrent import Suspend, Thenable, activity, suspense
from ryact_testkit import create_noop_root


def _suspender(thenable: Thenable) -> Any:
    def C(**_: Any) -> Any:
        raise Suspend(thenable)

    return C


def test_basic_example_of_suspending_inside_hidden_tree() -> None:
    root = create_noop_root()
    t = Thenable()
    Child = _suspender(t)

    root.render(
        create_element(
            activity,
            {
                "mode": "hidden",
                "children": suspense(
                    fallback=create_element("div", {"id": "fb"}),
                    children=create_element(Child, {}),
                ),
            },
        )
    )
    # Hidden activity does not commit fallback or content.
    assert root.get_children_snapshot() is None


def test_update_that_suspends_inside_hidden_tree_does_not_infinite_loop() -> None:
    root = create_noop_root()
    t = Thenable()
    Child = _suspender(t)

    # Start hidden + suspended.
    root.render(
        create_element(
            activity,
            {
                "mode": "hidden",
                "children": suspense(
                    fallback=create_element("div", {"id": "fb"}),
                    children=create_element(Child, {}),
                ),
            },
        )
    )
    assert root.get_children_snapshot() is None

    # Resolve while hidden: should not schedule a visible commit (noop host).
    t.resolve()
    assert root.get_children_snapshot() is None

    # Reveal: now the resolved thenable should allow content to render.
    root.render(
        create_element(
            activity,
            {
                "mode": "visible",
                "children": suspense(
                    fallback=create_element("div", {"id": "fb"}),
                    children=create_element("div", {"id": "ok"}),
                ),
            },
        )
    )
    snap = root.get_children_snapshot()
    assert isinstance(snap, dict)
    assert snap["type"] == "div"
    assert snap["props"]["id"] == "ok"


def test_legacyhidden_does_not_handle_suspense() -> None:
    root = create_noop_root()
    t = Thenable()
    Child = _suspender(t)

    root.render(
        create_element(
            activity,
            {
                "mode": "hidden",
                "children": suspense(
                    fallback=create_element("div", {"id": "fb"}),
                    children=create_element(Child, {}),
                ),
            },
        )
    )
    assert root.get_children_snapshot() is None
