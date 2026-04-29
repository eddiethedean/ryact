from __future__ import annotations

from dataclasses import dataclass
from typing import Any, AsyncIterator

from ryact import create_element
from ryact.concurrent import Suspend, Thenable, fragment, suspense_list
from ryact_testkit import create_noop_root
from ryact_testkit.warnings import WarningCapture


def _span(value: str) -> Any:
    return create_element("span", {"text": value})


def _texts(snapshot: Any) -> list[str]:
    if snapshot is None:
        return []
    if isinstance(snapshot, list):
        return [x["props"]["text"] for x in snapshot]
    return [snapshot["props"]["text"]]


def _suspense(*, key: str, fallback: str, child: Any) -> Any:
    return create_element(
        "__suspense__",
        {"fallback": _span(fallback), "children": (child,)},
        key=key,
    )


def test_displays_each_items_in_forwards_order() -> None:
    # Minimal model: forwards+hidden shows first fallback, then reveals sequentially.
    t1, t2 = Thenable(), Thenable()
    s1, s2 = {"r": False}, {"r": False}

    def A() -> Any:
        if not s1["r"]:
            raise Suspend(t1)
        return _span("A")

    def B() -> Any:
        if not s2["r"]:
            raise Suspend(t2)
        return _span("B")

    root = create_noop_root()
    root.render(
        suspense_list(
            reveal_order="forwards",
            tail="hidden",
            children=fragment(
                _suspense(key="a", fallback="A...", child=create_element(A)),
                _suspense(key="b", fallback="B...", child=create_element(B)),
            ),
        )
    )
    root.flush()
    assert _texts(root.get_children_snapshot()) == ["A..."]

    s1["r"] = True
    t1.resolve()
    root.flush()
    assert _texts(root.get_children_snapshot()) == ["A", "B..."]

    s2["r"] = True
    t2.resolve()
    root.flush()
    assert _texts(root.get_children_snapshot()) == ["A", "B"]


def test_displays_each_items_in_backwards_order() -> None:
    t1, t2 = Thenable(), Thenable()
    s1, s2 = {"r": False}, {"r": False}

    def A() -> Any:
        if not s1["r"]:
            raise Suspend(t1)
        return _span("A")

    def B() -> Any:
        if not s2["r"]:
            raise Suspend(t2)
        return _span("B")

    root = create_noop_root()
    root.render(
        suspense_list(
            reveal_order="backwards",
            tail="hidden",
            children=fragment(
                _suspense(key="a", fallback="A...", child=create_element(A)),
                _suspense(key="b", fallback="B...", child=create_element(B)),
            ),
        )
    )
    root.flush()
    # Backwards renders B first (tail hidden hides earlier items).
    assert _texts(root.get_children_snapshot()) == ["B..."]


def test_displays_each_items_in_backwards_order_legacy() -> None:
    # Legacy roots show content independently (no tail hiding coordination).
    root = create_noop_root(legacy=True)
    root.render(
        suspense_list(
            reveal_order="backwards",
            tail="hidden",
            children=fragment(_span("A"), _span("B")),
        )
    )
    root.flush()
    assert _texts(root.get_children_snapshot()) == ["A", "B"]


def test_shows_content_independently_with_revealorder_independent() -> None:
    root = create_noop_root()
    root.render(
        suspense_list(reveal_order="independent", children=fragment(_span("A"), _span("B")))
    )
    root.flush()
    assert _texts(root.get_children_snapshot()) == ["A", "B"]


def test_shows_content_independently_in_legacy_mode_regardless_of_option() -> None:
    root = create_noop_root(legacy=True)
    root.render(
        suspense_list(reveal_order="forwards", tail="hidden", children=fragment(_span("A"), _span("B")))
    )
    root.flush()
    assert _texts(root.get_children_snapshot()) == ["A", "B"]


def test_only_shows_one_loading_state_at_a_time_for_collapsed_tail_insertions() -> None:
    # Minimal collapsed tail: after first suspension, show only one fallback.
    t1, t2 = Thenable(), Thenable()
    s1, s2 = {"r": False}, {"r": False}

    def A() -> Any:
        if not s1["r"]:
            raise Suspend(t1)
        return _span("A")

    def B() -> Any:
        if not s2["r"]:
            raise Suspend(t2)
        return _span("B")

    root = create_noop_root()
    root.render(
        suspense_list(
            reveal_order="forwards",
            tail="collapsed",
            children=fragment(
                _suspense(key="a", fallback="A...", child=create_element(A)),
                _suspense(key="b", fallback="B...", child=create_element(B)),
            ),
        )
    )
    root.flush()
    assert _texts(root.get_children_snapshot()) == ["A..."]


def test_warns_for_async_generator_components_in_forwards_order() -> None:
    async def Gen() -> AsyncIterator[Any]:
        yield _span("A")

    with WarningCapture() as cap:
        root = create_noop_root()
        root.render(suspense_list(reveal_order="forwards", children=fragment(create_element(Gen))))
        root.flush()
    cap.assert_any("async")


def test_warns_if_a_nested_async_iterable_is_passed_to_a_forwards_list() -> None:
    async def Gen() -> AsyncIterator[Any]:
        yield _span("A")

    nested = fragment(create_element(Gen))
    with WarningCapture() as cap:
        root = create_noop_root()
        root.render(suspense_list(reveal_order="forwards", children=fragment(nested)))
        root.flush()
    cap.assert_any("async")

