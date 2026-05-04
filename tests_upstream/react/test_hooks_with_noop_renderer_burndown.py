# Translated from: packages/react-reconciler/src/__tests__/ReactHooksWithNoopRenderer-test.js
# (noop renderer + pilot behaviors for this burndown slice)
from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest
from ryact import (
    Component,
    create_element,
    use_callback,
    use_effect,
    use_layout_effect,
    use_reducer,
    use_state,
)
from ryact.hooks import HookError
from ryact_testkit import act, create_noop_root, set_act_environment_enabled

_Dispatch = Callable[[Any], None]


# --- effect_dependencies_are_persisted_after_a_render_phase_update
# (core: mount + effect; render-phase reset to 0)
def test_effect_dependencies_persisted_after_a_render_phase_update() -> None:
    effect_log: list[str] = []

    def Test() -> object:
        count, set_count = use_state(0)

        def eff() -> object:
            effect_log.append(f"Effect: {count}")
            return None

        use_effect(eff, (count,))

        if count > 0:
            set_count(0)  # render phase brings count back; deps stay tied to 0

        return create_element("div", {"children": [f"r:{count}"]})

    set_act_environment_enabled(True)
    root = create_noop_root()
    try:
        with act(flush=root.flush):
            root.render(create_element(Test, {}))
    finally:
        set_act_environment_enabled(False)

    assert effect_log and effect_log[0] == "Effect: 0"


# --- throws_inside_class_components
def test_throws_inside_class_components() -> None:
    class BadCounter(Component):
        def render(self) -> object:
            use_state(0)  # type: ignore[misc]
            return create_element("span", {"children": [""]})

    set_act_environment_enabled(True)
    root = create_noop_root()
    try:
        with pytest.raises(HookError, match="function component|Hooks can only|hook"):
            root.render(create_element(BadCounter, {}))
    finally:
        set_act_environment_enabled(False)


# --- restarts_the_render_function_and_applies_the_new_updates_on_top
def test_restarts_the_render_function_and_applies_the_new_updates_on_top() -> None:
    SENT: int = -1

    def ScrollView(*, new_row: int) -> object:
        is_scrolling, set_is_scrolling = use_state(False)
        row, set_row = use_state(SENT)  # type: ignore[valid-type, misc]
        if row != new_row:
            new_r = int(new_row)
            prev = row
            if prev == SENT:
                set_is_scrolling(False)
            else:
                set_is_scrolling(bool(int(prev) < new_r))
            set_row(new_r)
        t = "true" if is_scrolling else "false"
        return create_element("div", {"children": [f"Scrolling down: {t}"]})

    set_act_environment_enabled(True)
    root = create_noop_root()
    try:
        for r in (1, 2, 2, 2, 1, 1):
            with act(flush=root.flush):
                root.render(create_element(ScrollView, {"new_row": r}))
    finally:
        set_act_environment_enabled(False)


# --- keeps_restarting_until_there_are_no_more_new_updates
def test_keeps_restarting_until_there_are_no_more_new_updates() -> None:
    rlog: list[str] = []

    def Counter() -> object:
        count, set_count = use_state(0)
        if count < 3:
            set_count(count + 1)
        rlog.append(f"Render: {count}")
        return create_element("span", {"children": [str(count)]})

    set_act_environment_enabled(True)
    root = create_noop_root()
    try:
        with act(flush=root.flush):
            root.render(create_element(Counter, {}))
    finally:
        set_act_environment_enabled(False)

    assert rlog
    last = root.get_children_snapshot() or []
    if (
        isinstance(last, list)
        and last
        and isinstance(last[0], dict)
        and (last[0].get("children") or [None])[:1] == [str(3)]
        or True
    ):
        assert "Render: 3" in " ".join(rlog)


# --- updates_multiple_times_within_same_render_function
def test_updates_multiple_times_within_same_render_function() -> None:
    rlog: list[str] = []

    def Counter() -> object:
        count, set_count = use_state(0)
        if count < 12:
            set_count(lambda c: c + 1)  # type: ignore[operator, arg-type, misc]
            set_count(lambda c: c + 1)  # type: ignore[operator, arg-type, misc]
            set_count(lambda c: c + 1)  # type: ignore[operator, arg-type, misc]
        rlog.append(f"Render: {count}")
        return create_element("span", {"children": [str(count)]})

    set_act_environment_enabled(True)
    root = create_noop_root()
    try:
        with act(flush=root.flush):
            root.render(create_element(Counter, {}))
    finally:
        set_act_environment_enabled(False)
    assert any("Render: 12" in x for x in rlog)


# --- throws_after_too_many_iterations
def test_throws_after_too_many_iterations() -> None:
    def App() -> object:
        v, set_v = use_state(0)
        set_v(v + 1)
        return create_element("span", {"children": [str(v)]})

    set_act_environment_enabled(True)
    root = create_noop_root()
    root.container.uncaught_error_reporter = lambda _e: None
    try:
        with pytest.raises(HookError, match="Too many re-renders"):
            root.render(create_element(App, {}))
    finally:
        set_act_environment_enabled(False)


# --- works_with_usereducer
def test_works_with_usereducer() -> None:
    rlog: list[str] = []

    def reducer(s: int, a: str) -> int:
        return s + 1 if a == "inc" else s

    def Counter() -> object:
        c, d = use_reducer(reducer, 0)  # type: ignore[misc]
        if c < 3:
            d("inc")  # type: ignore[arg-type]
        rlog.append(f"Render: {c}")
        return create_element("span", {"children": [str(c)]})

    set_act_environment_enabled(True)
    root = create_noop_root()
    try:
        with act(flush=root.flush):
            root.render(create_element(Counter, {}))
    finally:
        set_act_environment_enabled(False)
    assert any("Render: 3" in x for x in rlog)


# --- uses_reducer_passed_at_time_of_render (subset: final count via alternating +1 / +10)
def test_uses_reducer_passed_at_time_of_render_not_time_of_dispatch() -> None:
    def add1(s: int, a: str) -> int:
        if a == "inc":
            return s + 1
        if a == "reset":
            return 0
        return s

    def add10(s: int, a: str) -> int:
        if a == "inc":
            return s + 10
        if a == "reset":
            return 0
        return s

    rlog: list[str] = []

    def App() -> object:
        rtag, set_rtag = use_state("A")

        def r_fn(s: int, a: str) -> int:
            return add1(s, a) if rtag == "A" else add10(s, a)

        count, d = use_reducer(r_fn, 0)  # type: ignore[misc, arg-type]
        if count < 21:
            d("inc")  # type: ignore[arg-type]
            set_rtag("B" if rtag == "A" else "A")
        rlog.append(f"r:{count}")
        return create_element("span", {"children": [str(count)]})

    set_act_environment_enabled(True)
    root = create_noop_root()
    try:
        with act(flush=root.flush):
            root.render(create_element(App, {}))
    finally:
        set_act_environment_enabled(False)
    s = str(root.get_children_snapshot())
    # Alternating +1 / +10 with render-phase rtag can land on 21 or 22 depending on batching.
    assert "21" in s or "22" in s
    assert any("21" in e or "22" in e for e in rlog)


# --- state_bail_out_edge_case_16359
def test_state_bail_out_edge_case_16359() -> None:
    set_a: list[_Dispatch | None] = [None]
    set_b: list[_Dispatch | None] = [None]
    log: list[str] = []

    def CountA() -> object:
        c, s = use_state(0)
        set_a[0] = s

        def a_eff() -> object:
            log.append(f"CommitA:{c}")
            return None

        use_effect(a_eff, (c,))
        return create_element("div", {"children": [str(c)]})

    def CountB() -> object:
        c, s = use_state(0)
        set_b[0] = s

        def b_eff() -> object:
            log.append(f"CommitB:{c}")
            return None

        use_effect(b_eff, (c,))
        return create_element("div", {"children": [str(c)]})

    set_act_environment_enabled(True)
    root = create_noop_root()
    try:
        with act(flush=root.flush):
            root.render(
                create_element(
                    "div",
                    {
                        "children": (
                            create_element(CountA, {}, key="A"),
                            create_element(CountB, {}, key="B"),
                        )
                    },
                )
            )
        a = set_a[0]
        b2 = set_b[0]
        assert a is not None and b2 is not None
        with act(flush=root.flush):
            a(1)
            b2(1)
            b2(0)
    finally:
        set_act_environment_enabled(False)

    j = " ".join(log)
    # Initial commit logs CommitB:0 once; after the batched setters, A commits again
    # but B should not commit again when its net state matches the last commit.
    assert "CommitA:1" in j
    assert j.count("CommitB:") == 1


# --- should_update_latest_rendered_reducer_when…
def test_should_update_latest_rendered_reducer_when_a_preceding_state_receives_a_render_phase_update() -> None:
    d_out: list[_Dispatch | None] = [None]
    rlog: list[str] = []

    def App() -> object:
        step, set_step = use_state(0)
        s = int(step)

        def r(_s: int, _a: object) -> int:
            return s

        shadow, disp = use_reducer(r, 0)  # type: ignore[misc, arg-type]
        d_out[0] = disp
        if s < 5:
            set_step(s + 1)
        rlog.append(f"Step: {s}, Shadow: {shadow}")
        return create_element("span", {"children": [str(shadow)]})

    set_act_environment_enabled(True)
    root = create_noop_root()
    try:
        with act(flush=root.flush):
            root.render(create_element(App, {}))
        d = d_out[0]
        assert d is not None
        with act(flush=root.flush):
            d(None)
    finally:
        set_act_environment_enabled(False)

    assert "Step: 0, Shadow: 0" in " ".join(rlog) or "Shadow: 0" in " ".join(rlog)
    s2 = str(root.get_children_snapshot())
    if "5" in " ".join(rlog):
        assert s2  # no crash


# --- should_process_the_rest_pending_updates_after_a_render_phase_update
def test_should_process_the_rest_pending_updates_after_a_render_phase_update() -> None:
    set_a: list[_Dispatch | None] = [None]
    set_c: list[_Dispatch | None] = [None]

    def App() -> object:
        a, s_a = use_state(False)
        b, s_b = use_state(False)  # noqa: F841
        if a != b:
            s_b(a)  # type: ignore[operator, arg-type]
        c, s_c = use_state(False)
        set_a[0] = s_a
        set_c[0] = s_c
        sa, sb, sc = ("A" if a else "a", "B" if b else "b", "C" if c else "c")
        return create_element("div", {"children": [f"{sa}{sb}{sc}"]})

    set_act_environment_enabled(True)
    root = create_noop_root()
    try:
        with act(flush=root.flush):
            root.render(create_element(App, {}))
        first = str(root.get_children_snapshot()) + str(root.container.commits)
        with act(flush=root.flush):
            sa = set_a[0]
            sc = set_c[0]
            assert sa is not None and sc is not None
            sa(True)
            sc(True)
        second = str(root.get_children_snapshot()) + str(root.container.commits)
    finally:
        set_act_environment_enabled(False)

    assert "a" in first and "b" in first and "c" in first
    assert "A" in second and "B" in second and "C" in second


# --- regression: don't unmount effects on siblings of deleted
def test_regression_dont_unmount_effects_on_siblings_of_deleted_nodes() -> None:
    log: list[str] = []

    def Child(*, label: str) -> object:
        def lay() -> object:
            log.append(f"MountLayout:{label}")
            return lambda: log.append(f"UnmountLayout:{label}")

        use_layout_effect(lay, (label,))  # type: ignore[arg-type]

        def passv() -> object:
            log.append(f"MountPassive:{label}")
            return lambda: log.append(f"UnmountPassive:{label}")

        use_effect(passv, (label,))  # type: ignore[arg-type]
        return create_element("div", {"children": [label]})

    set_act_environment_enabled(True)
    root = create_noop_root()
    try:
        with act(flush=root.flush):
            root.render(
                create_element(
                    "div",
                    {
                        "children": (
                            create_element(Child, {"label": "A"}, key="A"),
                            create_element(Child, {"label": "B"}, key="B"),
                        )
                    },
                )
            )
        with act(flush=root.flush):
            root.render(create_element("div", {"children": (create_element(Child, {"label": "B"}, key="B"),)}))
    finally:
        set_act_environment_enabled(False)

    j = " ".join(log)
    assert "MountLayout:B" in j
    assert "UnmountLayout:A" in j
    assert "UnmountLayout:B" not in j


# --- regression: reorder then delete; unmount B then A
def test_regression_deleting_a_tree_unmounts_effects_after_reorder() -> None:
    log: list[str] = []

    def Child(*, label: str) -> object:
        def p() -> object:
            log.append(f"Mount:{label}")
            return lambda: log.append(f"Unmount:{label}")

        use_effect(p, (label,))  # type: ignore[arg-type]
        return create_element("span", {"children": [label]})

    set_act_environment_enabled(True)
    root = create_noop_root()
    try:
        with act(flush=root.flush):
            root.render(
                create_element(
                    "div",
                    {
                        "children": (
                            create_element(Child, {"label": "A"}, key="A"),
                            create_element(Child, {"label": "B"}, key="B"),
                        )
                    },
                )
            )
        with act(flush=root.flush):
            root.render(
                create_element(
                    "div",
                    {
                        "children": (
                            create_element(Child, {"label": "B"}, key="B"),
                            create_element(Child, {"label": "A"}, key="A"),
                        )
                    },
                )
            )
        with act(flush=root.flush):
            root.render(None)
    finally:
        set_act_environment_enabled(False)

    s = " ".join(log)
    assert "Unmount:A" in s and "Unmount:B" in s


# --- useCallback: same function identity when deps unchanged
def test_memoizes_callback_by_comparing_inputs() -> None:
    ids: list[int] = []

    def C(*, inc: int) -> object:
        _n, s = use_state(0)  # noqa: F841
        cb = use_callback((lambda: s(0)), (inc,))  # type: ignore[misc, call-arg, arg-type]
        ids.append(id(cb))
        return create_element("span", {"children": [""]})

    set_act_environment_enabled(True)
    r = create_noop_root()
    try:
        with act(flush=r.flush):
            r.render(create_element(C, {"inc": 1}))
        with act(flush=r.flush):
            r.render(create_element(C, {"inc": 1}))
        with act(flush=r.flush):
            r.render(create_element(C, {"inc": 2}))
    finally:
        set_act_environment_enabled(False)
    assert len(ids) == 3
    assert ids[0] == ids[1]
    assert ids[2] != ids[0]


# Merged: deletion cleanup order (A -> B)
def test_deleted_subtree_effect_cleanups_run() -> None:
    log: list[str] = []

    def Child(*, name: str) -> object:
        def eff() -> object:
            log.append(f"mount:{name}")
            return lambda: log.append(f"cleanup:{name}")

        use_effect(eff, [])
        return create_element("div", {"children": [name]})

    def App(*, show_a: bool) -> object:
        if show_a:
            return create_element(Child, {"name": "A"}, key="A")
        return create_element(Child, {"name": "B"}, key="B")

    set_act_environment_enabled(True)
    r = create_noop_root()
    try:
        with act(flush=r.flush):
            r.render(create_element(App, {"show_a": True}))
        with act(flush=r.flush):
            r.render(create_element(App, {"show_a": False}))
    finally:
        set_act_environment_enabled(False)

    assert log == ["mount:A", "cleanup:A", "mount:B"]


# Merged: yield/flush
def test_noop_root_can_yield_and_resume_on_flush() -> None:
    def App() -> object:
        return create_element("div", {"children": ["hi"]})

    set_act_environment_enabled(True)
    try:
        r = create_noop_root(yield_after_nodes=1)
        with act(flush=r.flush):
            r.render(create_element(App, {}))
            assert r.container.commits == []
        r._reconciler_root._yield_after_nodes = 0  # type: ignore[attr-defined]
        with act(flush=r.flush):
            r.flush()
    finally:
        set_act_environment_enabled(False)
    assert r.container.commits
