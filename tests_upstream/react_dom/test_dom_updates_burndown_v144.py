# Translated from: packages/react-dom/src/__tests__/ReactUpdates-test.js
# Burndown v144: state update batching (noop harness; host-agnostic scheduling).
from __future__ import annotations

from typing import Any, cast

import pytest
from ryact import Component, create_element, use_layout_effect, use_state
from ryact_testkit import act, create_noop_root, set_act_environment_enabled


def _snap_text(root: Any) -> str:
    snap = root.get_children_snapshot()
    if isinstance(snap, dict):
        return str(snap.get("props", {}).get("text", snap))
    return str(snap)


def test_should_batch_state_when_updating_state_twice() -> None:
    log: list[str] = []
    state_box: dict[str, Any] = {}
    setter_box: dict[str, Any] = {}

    def App() -> object:
        state, set_state = use_state(0)
        state_box["v"] = state
        setter_box["set"] = set_state

        def le() -> None:
            log.append("Commit")

        use_layout_effect(le, (state,))
        return create_element("span", {"text": str(state)})

    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        with act(flush=root.flush):
            root.render(create_element(App))
        assert log == ["Commit"]
        assert _snap_text(root) == "0"

        log.clear()
        with act(flush=root.flush):
            cast(Any, setter_box["set"])(1)
            cast(Any, setter_box["set"])(2)
            assert state_box["v"] == 0
            assert _snap_text(root) == "0"
            assert log == []

        assert state_box["v"] == 2
        assert log == ["Commit"]
        assert _snap_text(root) == "2"
    finally:
        set_act_environment_enabled(False)


def test_should_batch_state_when_updating_two_different_states() -> None:
    log: list[str] = []
    box: dict[str, Any] = {}

    def App() -> object:
        a, set_a = use_state(0)
        b, set_b = use_state(0)
        box.update({"a": a, "b": b, "set_a": set_a, "set_b": set_b})

        def le() -> None:
            log.append("Commit")

        use_layout_effect(le, (a, b))
        return create_element("span", {"text": f"{a},{b}"})

    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        with act(flush=root.flush):
            root.render(create_element(App))
        log.clear()
        with act(flush=root.flush):
            cast(Any, box["set_a"])(1)
            cast(Any, box["set_b"])(2)
            assert box["a"] == 0 and box["b"] == 0
        assert box["a"] == 1 and box["b"] == 2
        assert _snap_text(root) == "1,2"
        assert log == ["Commit"]
    finally:
        set_act_environment_enabled(False)


def test_should_batch_parent_child_state_updates_together() -> None:
    log: list[str] = []
    box: dict[str, Any] = {}

    def Child(*, prop: int) -> object:
        state, set_state = use_state(0)
        box["child"] = state
        box["set_child"] = set_state

        def le() -> None:
            log.append("Child Commit")

        use_layout_effect(le, (state, prop))
        return create_element("span", {"text": f"{prop} {state}"})

    def Parent() -> object:
        state, set_state = use_state(0)
        box["parent"] = state
        box["set_parent"] = set_state

        def le() -> None:
            log.append("Parent Commit")

        use_layout_effect(le, (state,))
        return create_element(Child, {"prop": state})

    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        with act(flush=root.flush):
            root.render(create_element(Parent))
        assert log == ["Parent Commit", "Child Commit"]
        assert _snap_text(root) == "0 0"
        log.clear()
        with act(flush=root.flush):
            cast(Any, box["set_parent"])(1)
            cast(Any, box["set_child"])(2)
            assert box["parent"] == 0 and box["child"] == 0
        assert _snap_text(root) == "1 2"
        assert log == ["Parent Commit", "Child Commit"]
    finally:
        set_act_environment_enabled(False)


def test_should_batch_child_parent_state_updates_together() -> None:
    log: list[str] = []
    box: dict[str, Any] = {}

    def Child(*, prop: int) -> object:
        state, set_state = use_state(0)
        box["child"] = state
        box["set_child"] = set_state

        def le() -> None:
            log.append("Child Commit")

        use_layout_effect(le, (state, prop))
        return create_element("span", {"text": f"{prop} {state}"})

    def Parent() -> object:
        state, set_state = use_state(0)
        box["parent"] = state
        box["set_parent"] = set_state

        def le() -> None:
            log.append("Parent Commit")

        use_layout_effect(le, (state,))
        return create_element(Child, {"prop": state})

    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        with act(flush=root.flush):
            root.render(create_element(Parent))
        log.clear()
        with act(flush=root.flush):
            cast(Any, box["set_child"])(2)
            cast(Any, box["set_parent"])(1)
        assert _snap_text(root) == "1 2"
        assert log == ["Parent Commit", "Child Commit"]
    finally:
        set_act_environment_enabled(False)


def test_does_not_rerender_if_state_update_is_null() -> None:
    renders = {"n": 0}

    class App(Component):
        def render(self) -> object:
            renders["n"] += 1
            return create_element("span", {"text": str(self.state.get("x", 0))})

    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        with act(flush=root.flush):
            root.render(create_element(App))
        n0 = renders["n"]
        fiber = root._reconciler_root.current.child  # type: ignore[union-attr]
        inst = fiber.state_node
        with act(flush=root.flush):
            inst.set_state(None)
        assert renders["n"] == n0
    finally:
        set_act_environment_enabled(False)


def test_should_support_chained_state_updates() -> None:
    box: dict[str, Any] = {}

    def App() -> object:
        state, set_state = use_state(0)
        box["v"] = state
        box["set"] = set_state
        return create_element("span", {"text": str(state)})

    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        with act(flush=root.flush):
            root.render(create_element(App))
        with act(flush=root.flush):
            cast(Any, box["set"])(lambda n: n + 1)
            cast(Any, box["set"])(lambda n: n + 1)
        assert box["v"] == 2
        assert _snap_text(root) == "2"
    finally:
        set_act_environment_enabled(False)


def test_should_queue_nested_updates() -> None:
    log: list[str] = []
    box: dict[str, Any] = {}

    def Child() -> object:
        state, set_state = use_state(0)
        box["set"] = set_state

        def le() -> None:
            log.append(f"child {state}")

        use_layout_effect(le, (state,))
        return create_element("span", {"text": str(state)})

    def Parent() -> object:
        def le() -> None:
            log.append("parent")
            cast(Any, box["set"])(1)

        use_layout_effect(le, ())
        return create_element(Child)

    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        with act(flush=root.flush):
            root.render(create_element(Parent))
        assert log == ["parent", "child 0", "child 1"]
        assert _snap_text(root) == "1"
    finally:
        set_act_environment_enabled(False)


def test_mounts_and_unmounts_are_batched() -> None:
    log: list[str] = []

    class Child(Component):
        def componentDidMount(self) -> None:  # noqa: N802
            log.append("mount")

        def componentWillUnmount(self) -> None:  # noqa: N802
            log.append("unmount")

        def render(self) -> object:
            return create_element("span", {"text": "c"})

    show = {"v": True}

    def App() -> object:
        return create_element(Child) if show["v"] else None

    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        with act(flush=root.flush):
            root.render(create_element(App))
        assert log == ["mount"]
        log.clear()
        with act(flush=root.flush):
            show["v"] = False
            root.render(create_element(App))
        assert log == ["unmount"]
    finally:
        set_act_environment_enabled(False)


def test_throws_in_setstate_if_the_update_callback_is_not_a_function() -> None:
    class App(Component):
        def render(self) -> object:
            return create_element("span", {"text": "x"})

    root = create_noop_root()
    root.render(create_element(App))
    root.flush()
    inst = root._reconciler_root.current.child.state_node  # type: ignore[union-attr]
    with pytest.raises((TypeError, ValueError)):
        inst.set_state(123, callback=456)  # type: ignore[arg-type]


def test_should_flush_updates_in_the_correct_order() -> None:
    log: list[str] = []

    def App() -> object:
        a, set_a = use_state(0)
        b, set_b = use_state(0)

        def le() -> None:
            log.append(f"{a},{b}")

        use_layout_effect(le, (a, b))
        if a == 0:
            set_a(1)
        if b == 0:
            set_b(1)
        return create_element("span", {"text": f"{a},{b}"})

    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        with act(flush=root.flush):
            root.render(create_element(App))
        assert _snap_text(root) == "1,1"
        assert log == ["1,1"]
    finally:
        set_act_environment_enabled(False)
