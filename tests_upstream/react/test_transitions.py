from __future__ import annotations

from collections.abc import Callable

from ryact import create_element
from ryact.concurrent import start_transition
from ryact_testkit import create_noop_root


def test_should_render_normal_pri_updates_scheduled_after_transitions_before_transitions() -> None:
    # Upstream: ReactTransition-test.js
    # "should render normal pri updates scheduled after transitions before transitions"
    root = create_noop_root()

    set_a: Callable[[str], None] | None = None
    set_b: Callable[[str], None] | None = None

    def App() -> object:
        nonlocal set_a, set_b
        from ryact.hooks import use_state

        a, set_a_local = use_state("A")
        b, set_b_local = use_state("B")
        set_a = set_a_local
        set_b = set_b_local
        return create_element("div", {"a": a, "b": b})

    root.render(create_element(App))
    assert root.container.last_committed == {
        "type": "div",
        "key": None,
        "props": {"a": "A", "b": "B"},
        "children": [],
    }

    assert set_a is not None
    assert set_b is not None
    start_transition(lambda: set_a("T"))
    set_b("N")
    root.flush()

    # Normal priority update commits before the transition update.
    assert root.container.commits[-2:] == [
        {"type": "div", "key": None, "props": {"a": "A", "b": "N"}, "children": []},
        {"type": "div", "key": None, "props": {"a": "T", "b": "N"}, "children": []},
    ]
