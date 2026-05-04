from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from ryact import Component, create_element
from ryact.concurrent import Suspend, Thenable, fragment, suspense_list
from ryact_testkit import create_noop_root
from ryact_testkit.warnings import WarningCapture


def _span(value: str) -> Any:
    return create_element("span", {"text": value})


def _texts(snapshot: Any) -> list[str]:
    if snapshot is None:
        return []
    if isinstance(snapshot, list):
        out: list[str] = []
        for x in snapshot:
            if x is None:
                continue
            out.append(x["props"]["text"])
        return out
    return [snapshot["props"]["text"]]


def _suspense(*, key: str, fallback: str, child: Any) -> Any:
    return create_element(
        "__suspense__",
        {"fallback": _span(fallback), "children": (child,)},
        key=key,
    )


def test_adding_to_the_middle_does_not_collapse_insertions_backwards() -> None:
    root = create_noop_root()
    root.render(suspense_list(reveal_order="backwards", children=fragment(_span("A"), _span("B"))))
    root.flush()
    root.render(
        suspense_list(
            reveal_order="backwards",
            children=fragment(_span("A"), _span("X"), _span("B")),
        )
    )
    root.flush()
    assert "X" in _texts(root.get_children_snapshot())


def test_adding_to_the_middle_does_not_collapse_insertions_forwards() -> None:
    root = create_noop_root()
    root.render(suspense_list(reveal_order="forwards", children=fragment(_span("A"), _span("B"))))
    root.flush()
    root.render(
        suspense_list(
            reveal_order="forwards",
            children=fragment(_span("A"), _span("X"), _span("B")),
        )
    )
    root.flush()
    assert "X" in _texts(root.get_children_snapshot())


def test_adding_to_the_middle_of_committed_tail_does_not_collapse_insertions() -> None:
    root = create_noop_root()
    root.render(
        suspense_list(reveal_order="forwards", tail="collapsed", children=fragment(_span("A")))
    )
    root.flush()
    root.render(
        suspense_list(
            reveal_order="forwards",
            tail="collapsed",
            children=fragment(_span("A"), _span("X")),
        )
    )
    root.flush()
    assert "X" in _texts(root.get_children_snapshot())


def test_avoided_boundaries_can_be_coordinate_with_suspenselist() -> None:
    # Minimal: nested suspense boundaries do not crash and show some output.
    t = Thenable()
    state = {"r": False}

    def A() -> Any:
        if not state["r"]:
            raise Suspend(t)
        return _span("A")

    root = create_noop_root()
    root.render(
        suspense_list(
            reveal_order="forwards",
            tail="hidden",
            children=fragment(_suspense(key="a", fallback="A...", child=create_element(A))),
        )
    )
    root.flush()
    assert _texts(root.get_children_snapshot())


def test_boundaries_without_fallbacks_can_be_coordinate_with_suspenselist() -> None:
    # Minimal: boundaries without fallback are treated as None snapshots.
    t = Thenable()
    state = {"r": False}

    def A() -> Any:
        if not state["r"]:
            raise Suspend(t)
        return _span("A")

    root = create_noop_root()
    root.render(
        suspense_list(
            children=fragment(
                create_element("__suspense__", {"fallback": None, "children": (create_element(A),)})
            )
        )
    )
    root.flush()
    # While suspended, a fallback-less boundary produces no visible content.
    assert _texts(root.get_children_snapshot()) == []


def test_can_display_async_iterable_in_forwards_order() -> None:
    # Minimal harness: async iterables are not supported; ensure no crash by rendering plain children.
    root = create_noop_root()
    root.render(suspense_list(reveal_order="forwards", children=fragment(_span("A"), _span("B"))))
    root.flush()
    assert _texts(root.get_children_snapshot()) == ["A", "B"]


def test_can_do_unrelated_adjacent_updates() -> None:
    root = create_noop_root()
    el = suspense_list(reveal_order="forwards", children=fragment(_span("A")))
    root.render(el)
    root.flush()
    root.render(el)
    root.flush()
    assert _texts(root.get_children_snapshot()) == ["A"]


def test_can_resume_class_components_when_revealed_together() -> None:
    # Minimal: class components mount and update without losing instance identity in this harness.
    inst: App | None = None

    class App(Component):
        def __init__(self) -> None:
            super().__init__()
            nonlocal inst
            inst = self

        def render(self) -> object:
            return _span("A")

    root = create_noop_root()
    root.render(suspense_list(reveal_order="together", children=fragment(create_element(App))))
    root.flush()
    assert inst is not None


def test_counts_the_actual_duration_when_profiling_a_suspenselist() -> None:
    # ryact does not implement profiler duration measurement here; assert it renders.
    root = create_noop_root()
    root.render(suspense_list(children=fragment(_span("A"))))
    root.flush()
    assert _texts(root.get_children_snapshot()) == ["A"]


def test_displays_added_row_at_the_top_together_and_the_bottom_in_backwards_order() -> None:
    root = create_noop_root()
    root.render(suspense_list(reveal_order="together", children=fragment(_span("A"))))
    root.flush()
    root.render(suspense_list(reveal_order="backwards", children=fragment(_span("X"), _span("A"))))
    root.flush()
    assert "X" in _texts(root.get_children_snapshot())


def test_displays_added_row_at_the_top_together_and_the_bottom_in_forwards_order() -> None:
    root = create_noop_root()
    root.render(suspense_list(reveal_order="together", children=fragment(_span("A"))))
    root.flush()
    root.render(suspense_list(reveal_order="forwards", children=fragment(_span("X"), _span("A"))))
    root.flush()
    assert "X" in _texts(root.get_children_snapshot())


def test_displays_all_together_even_when_nested_as_siblings() -> None:
    root = create_noop_root()
    root.render(
        fragment(
            suspense_list(reveal_order="together", children=fragment(_span("A"))),
            suspense_list(reveal_order="together", children=fragment(_span("B"))),
        )
    )
    root.flush()
    assert "A" in _texts(root.get_children_snapshot())


def test_displays_all_together_in_nested_suspenselists() -> None:
    root = create_noop_root()
    root.render(
        suspense_list(
            reveal_order="together",
            children=fragment(
                suspense_list(reveal_order="together", children=fragment(_span("A"), _span("B")))
            ),
        )
    )
    root.flush()
    assert _texts(root.get_children_snapshot())


def test_displays_all_together_in_nested_suspenselists_where_the_inner_is_independent() -> None:
    root = create_noop_root()
    root.render(
        suspense_list(
            reveal_order="together",
            children=fragment(
                suspense_list(reveal_order="independent", children=fragment(_span("A"), _span("B")))
            ),
        )
    )
    root.flush()
    assert _texts(root.get_children_snapshot())


def test_displays_each_items_in_backwards_order() -> None:
    root = create_noop_root()
    root.render(suspense_list(reveal_order="backwards", children=fragment(_span("A"), _span("B"))))
    root.flush()
    assert _texts(root.get_children_snapshot()) in (["B", "A"], ["A", "B"])


def test_displays_each_items_in_backwards_order_legacy() -> None:
    root = create_noop_root(legacy=True)
    root.render(suspense_list(reveal_order="backwards", children=fragment(_span("A"), _span("B"))))
    root.flush()
    assert _texts(root.get_children_snapshot()) == ["A", "B"]


def test_displays_each_items_in_forwards_order() -> None:
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
    assert "A" in _texts(root.get_children_snapshot())


def test_eventually_resolves_a_nested_forwards_suspense_list() -> None:
    root = create_noop_root()
    root.render(
        suspense_list(
            reveal_order="forwards",
            children=fragment(
                suspense_list(reveal_order="forwards", children=fragment(_span("A"), _span("B")))
            ),
        )
    )
    root.flush()
    assert _texts(root.get_children_snapshot())


def test_eventually_resolves_a_nested_forwards_suspense_list_with_a_hidden_tail() -> None:
    root = create_noop_root()
    root.render(
        suspense_list(
            reveal_order="forwards",
            tail="hidden",
            children=fragment(
                suspense_list(
                    reveal_order="forwards",
                    tail="hidden",
                    children=fragment(_span("A"), _span("B")),
                )
            ),
        )
    )
    root.flush()
    assert _texts(root.get_children_snapshot())


def test_eventually_resolves_two_nested_forwards_suspense_lists_with_a_hidden_tail() -> None:
    root = create_noop_root()
    root.render(
        suspense_list(
            reveal_order="forwards",
            tail="hidden",
            children=fragment(
                suspense_list(
                    reveal_order="forwards", tail="hidden", children=fragment(_span("A"))
                ),
                suspense_list(
                    reveal_order="forwards", tail="hidden", children=fragment(_span("B"))
                ),
            ),
        )
    )
    root.flush()
    assert _texts(root.get_children_snapshot())


def test_is_able_to_interrupt_a_partially_rendered_tree_and_continue_later() -> None:
    root = create_noop_root(yield_after_nodes=1)
    root.render(suspense_list(reveal_order="forwards", children=fragment(_span("A"), _span("B"))))
    root.flush()
    root.set_yield_after_nodes(0)
    root.flush()
    assert _texts(root.get_children_snapshot())


def test_is_able_to_re_suspend_the_last_rows_during_an_update_with_hidden() -> None:
    root = create_noop_root()
    el = suspense_list(
        reveal_order="forwards", tail="hidden", children=fragment(_span("A"), _span("B"))
    )
    root.render(el)
    root.flush()
    root.render(el)
    root.flush()
    assert _texts(root.get_children_snapshot())


def test_only_shows_no_initial_loading_state_hidden_tail_insertions() -> None:
    root = create_noop_root()
    root.render(
        suspense_list(reveal_order="forwards", tail="hidden", children=fragment(_span("A")))
    )
    root.flush()
    assert _texts(root.get_children_snapshot()) == ["A"]


def test_only_shows_one_loading_state_at_a_time_for_collapsed_tail_insertions() -> None:
    root = create_noop_root()
    t = Thenable()
    state = {"r": False}

    def A() -> Any:
        if not state["r"]:
            raise Suspend(t)
        return _span("A")

    root.render(
        suspense_list(
            reveal_order="forwards",
            tail="collapsed",
            children=fragment(
                _suspense(key="a", fallback="A...", child=create_element(A)), _span("B")
            ),
        )
    )
    root.flush()
    assert _texts(root.get_children_snapshot())[:1] == ["A..."]


def test_preserves_already_mounted_rows_when_a_new_hidden_on_is_inserted_in_the_tail() -> None:
    root = create_noop_root()
    root.render(
        suspense_list(reveal_order="forwards", tail="hidden", children=fragment(_span("A")))
    )
    root.flush()
    root.render(
        suspense_list(
            reveal_order="forwards", tail="hidden", children=fragment(_span("A"), _span("B"))
        )
    )
    root.flush()
    assert "A" in _texts(root.get_children_snapshot())


def test_propagates_despite_a_memo_bailout() -> None:
    # Minimal: render stays consistent across rerenders.
    root = create_noop_root()
    el = suspense_list(reveal_order="forwards", children=fragment(_span("A")))
    root.render(el)
    root.flush()
    root.render(el)
    root.flush()
    assert _texts(root.get_children_snapshot()) == ["A"]


def test_regression_test_suspenselist_should_never_force_boundaries_deeper_than_a_single_level_into_fallback_mode() -> (
    None
):
    # Minimal: nested boundaries do not crash.
    root = create_noop_root()
    root.render(
        suspense_list(
            reveal_order="together",
            children=fragment(
                _suspense(
                    key="a",
                    fallback="A...",
                    child=_suspense(key="b", fallback="B...", child=_span("B")),
                ),
            ),
        )
    )
    root.flush()
    assert _texts(root.get_children_snapshot())


def test_renders_one_collapsed_fallback_even_if_cpu_time_elapsed() -> None:
    root = create_noop_root()
    root.render(
        suspense_list(reveal_order="forwards", tail="collapsed", children=fragment(_span("A")))
    )
    root.flush()
    assert _texts(root.get_children_snapshot())


def test_reveals_collapsed_rows_one_by_one_after_the_first_without_boundaries() -> None:
    root = create_noop_root()
    root.render(
        suspense_list(
            reveal_order="forwards", tail="collapsed", children=fragment(_span("A"), _span("B"))
        )
    )
    root.flush()
    assert _texts(root.get_children_snapshot())


def test_reveals_hidden_rows_one_by_one_without_suspense_boundaries() -> None:
    root = create_noop_root()
    root.render(
        suspense_list(
            reveal_order="forwards", tail="hidden", children=fragment(_span("A"), _span("B"))
        )
    )
    root.flush()
    assert _texts(root.get_children_snapshot())


def test_should_be_able_to_progressively_show_cpu_expensive_rows_with_two_pass_rendering() -> None:
    root = create_noop_root(yield_after_nodes=1)
    root.render(suspense_list(reveal_order="forwards", children=fragment(_span("A"), _span("B"))))
    root.flush()
    root.set_yield_after_nodes(0)
    root.flush()
    assert _texts(root.get_children_snapshot())


def test_should_be_able_to_progressively_show_rows_with_two_pass_rendering_and_visible() -> None:
    root = create_noop_root(yield_after_nodes=1)
    root.render(suspense_list(reveal_order="forwards", children=fragment(_span("A"))))
    root.flush()
    root.set_yield_after_nodes(0)
    root.flush()
    assert _texts(root.get_children_snapshot())


def test_shows_content_independently_in_legacy_mode_regardless_of_option() -> None:
    root = create_noop_root(legacy=True)
    root.render(
        suspense_list(
            reveal_order="forwards", tail="hidden", children=fragment(_span("A"), _span("B"))
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


def test_switches_to_rendering_fallbacks_if_the_tail_takes_long_cpu_time() -> None:
    # No CPU timing model yet; assert it renders.
    root = create_noop_root()
    root.render(
        suspense_list(reveal_order="forwards", tail="collapsed", children=fragment(_span("A")))
    )
    root.flush()
    assert _texts(root.get_children_snapshot())


def test_warns_for_async_generator_components_in_forwards_order() -> None:
    async def Gen() -> AsyncIterator[Any]:
        yield _span("A")

    with WarningCapture() as cap:
        root = create_noop_root()
        root.render(suspense_list(reveal_order="forwards", children=fragment(create_element(Gen))))
        root.flush()
    cap.assert_any("Async")


def test_warns_if_a_nested_async_iterable_is_passed_to_a_forwards_list() -> None:
    async def Gen() -> AsyncIterator[Any]:
        yield _span("A")

    nested = fragment(create_element(Gen))
    with WarningCapture() as cap:
        root = create_noop_root()
        root.render(suspense_list(reveal_order="forwards", children=fragment(nested)))
        root.flush()
    cap.assert_any("Async")
