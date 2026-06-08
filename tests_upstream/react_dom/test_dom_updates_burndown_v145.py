# Translated from: packages/react-dom/src/__tests__/ReactUpdates-test.js
# Burndown v145: batching, lifecycle ordering, and update guards (noop harness).
from __future__ import annotations

import random
from typing import Any, cast

import pytest
from ryact import Component, create_element, create_ref, use_layout_effect, use_state
from ryact_testkit import act, create_noop_root, set_act_environment_enabled


def _snap_text(root: Any) -> str:
    snap = root.get_children_snapshot()
    if isinstance(snap, dict):
        return str(snap.get("props", {}).get("text", snap))
    return str(snap)


def test_should_batch_state_and_props_together() -> None:
    log: list[str] = []
    box: dict[str, Any] = {}

    def ComponentFn(*, prop: int) -> object:
        state, set_state = use_state(0)
        box.update({"prop": prop, "state": state, "set": set_state})

        def le() -> None:
            log.append("Commit")

        use_layout_effect(le, (prop, state))
        return create_element("span", {"text": f"{prop} {state}"})

    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        with act(flush=root.flush):
            root.render(create_element(ComponentFn, {"prop": 0}))
        assert log == ["Commit"]
        assert _snap_text(root) == "0 0"

        log.clear()
        with act(flush=root.flush):
            root.batched_updates(
                lambda: (
                    root.render(create_element(ComponentFn, {"prop": 1})),
                    cast(Any, box["set"])(2),
                )
            )
            assert box["prop"] == 0 and box["state"] == 0
            assert _snap_text(root) == "0 0"
            assert log == []

        assert box["prop"] == 1 and box["state"] == 2
        assert log == ["Commit"]
        assert _snap_text(root) == "1 2"
    finally:
        set_act_environment_enabled(False)


def test_should_flow_updates_correctly() -> None:
    will_updates: list[str] = []
    did_updates: list[str] = []
    refs: dict[str, Any] = {}

    def _mixin_will(self: Component) -> None:
        will_updates.append(getattr(type(self), "displayName", type(self).__name__))

    def _mixin_did(self: Component) -> None:
        did_updates.append(getattr(type(self), "displayName", type(self).__name__))

    class Box(Component):
        displayName = "Box"

        def componentWillUpdate(self, _np: object, _ns: object) -> None:  # noqa: N802
            _mixin_will(self)

        def componentDidUpdate(self, *_args: object) -> None:  # noqa: N802
            _mixin_did(self)

        def render(self) -> object:
            return create_element("div", {"ref": refs.setdefault("boxDiv", create_ref())}, self.props["children"])

    class Child(Component):
        displayName = "Child"

        def componentWillUpdate(self, _np: object, _ns: object) -> None:  # noqa: N802
            _mixin_will(self)

        def componentDidUpdate(self, *_args: object) -> None:  # noqa: N802
            _mixin_did(self)

        def render(self) -> object:
            return create_element("span", {"ref": refs.setdefault("span", create_ref())})

    class Switcher(Component):
        displayName = "Switcher"

        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self._state = {"tabKey": "hello"}
            refs["switcher"] = self
            refs["box"] = create_ref()

        def componentWillUpdate(self, _np: object, _ns: object) -> None:  # noqa: N802
            _mixin_will(self)

        def componentDidUpdate(self, *_args: object) -> None:  # noqa: N802
            _mixin_did(self)

        def render(self) -> object:
            child = self.props["children"]
            tab = self.state["tabKey"]
            child_key = getattr(child, "key", None)
            display = "" if tab == child_key else "none"
            return create_element(
                Box,
                {"ref": refs["box"]},
                create_element(
                    "div", {"ref": refs.setdefault("switcherDiv", create_ref()), "style": {"display": display}}, child
                ),
            )

    class App(Component):
        displayName = "App"

        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            refs["app"] = self
            refs["child"] = create_ref()

        def render(self) -> object:
            return create_element(
                Switcher,
                {"ref": refs.setdefault("switcherRef", create_ref())},
                create_element(Child, {"key": "hello", "ref": refs["child"]}),
            )

    def expect_updates(desired_will: list[str], desired_did: list[str]) -> None:
        for name in desired_will:
            assert name in will_updates
        for name in desired_did:
            assert name in did_updates
        will_updates.clear()
        did_updates.clear()

    def trigger_update(c: Component) -> None:
        c.set_state({"x": 1})

    def test_updates(components: list[Component], desired_will: list[str], desired_did: list[str]) -> None:
        with act(flush=root.flush):
            for c in components:
                trigger_update(c)
        expect_updates(desired_will, desired_did)
        with act(flush=root.flush):
            for c in reversed(components):
                trigger_update(c)
        expect_updates(desired_will, desired_did)

    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        with act(flush=root.flush):
            root.render(create_element(App))

        switcher = cast(Component, refs["switcherRef"].current)
        box_inst = cast(Component, refs["box"].current)
        child_inst = cast(Component, refs["child"].current)

        test_updates([box_inst, switcher], ["Switcher", "Box"], ["Box", "Switcher"])
        test_updates([child_inst, box_inst], ["Box", "Child"], ["Box", "Child"])
        test_updates([child_inst, switcher], ["Switcher", "Box", "Child"], ["Box", "Switcher", "Child"])
    finally:
        set_act_environment_enabled(False)


def test_should_queue_updates_from_during_mount() -> None:
    a_box: dict[str, Any] = {}

    class A(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self._state = {"x": 0}

        def componentWillMount(self) -> None:  # noqa: N802
            a_box["a"] = self

        def render(self) -> object:
            return create_element("span", {"text": f"A{self.state['x']}"})

    class B(Component):
        def componentWillMount(self) -> None:  # noqa: N802
            cast(Any, a_box["a"]).set_state({"x": 1})

        def render(self) -> object:
            return create_element("span", {"text": "B"})

    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        with act(flush=root.flush):
            root.render(create_element("div", {"children": (create_element(A), create_element(B))}))
            root.flush()
        assert a_box["a"].state["x"] == 1
    finally:
        set_act_environment_enabled(False)


def test_does_not_call_render_after_a_component_has_been_deleted() -> None:
    log: list[str] = []
    comp_a: dict[str, Any] = {}
    comp_b: dict[str, Any] = {}

    class B(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self._state = {"updates": 0}

        def componentDidMount(self) -> None:  # noqa: N802
            comp_b["inst"] = self

        def render(self) -> object:
            log.append("B")
            return create_element("span", {"text": "b"})

    class A(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self._state = {"showB": True}

        def componentDidMount(self) -> None:  # noqa: N802
            comp_a["inst"] = self

        def render(self) -> object:
            return create_element(B) if self.state["showB"] else create_element("span", {"text": "x"})

    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        with act(flush=root.flush):
            root.render(create_element(A))
        assert log == ["B"]
        log.clear()
        with act(flush=root.flush):
            comp_b["inst"].set_state({"updates": 1})
            comp_a["inst"].set_state({"showB": False})
        assert log == []
    finally:
        set_act_environment_enabled(False)


def test_throws_in_forceupdate_if_the_update_callback_is_not_a_function() -> None:
    class A(Component):
        def render(self) -> object:
            return create_element("span", {"text": "x"})

    root = create_noop_root()
    root.render(create_element(A))
    root.flush()
    inst = root._reconciler_root.current.child.state_node  # type: ignore[union-attr]
    with pytest.raises((TypeError, ValueError)):
        inst.force_update("no")  # type: ignore[arg-type]
    with pytest.raises((TypeError, ValueError)):
        inst.force_update({"foo": "bar"})  # type: ignore[arg-type]


def test_does_not_update_one_component_twice_in_a_batch_2410() -> None:
    parent_box: dict[str, Any] = {}
    child_ref = create_ref()
    render_count = {"n": 0}
    post_render_count = {"n": 0}
    once = {"v": False}

    class Child(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self._state = {"updated": False}

        def componentWillUpdate(self, _np: object, _ns: object) -> None:  # noqa: N802
            if not once["v"]:
                once["v"] = True
                self.set_state({"updated": True})

        def componentDidMount(self) -> None:  # noqa: N802
            assert render_count["n"] == post_render_count["n"] + 1
            post_render_count["n"] += 1

        def componentDidUpdate(self, *_args: object) -> None:  # noqa: N802
            assert render_count["n"] == post_render_count["n"] + 1
            post_render_count["n"] += 1

        def render(self) -> object:
            assert render_count["n"] == post_render_count["n"]
            render_count["n"] += 1
            return create_element("span", {"text": "c"})

    class Parent(Component):
        def componentDidMount(self) -> None:  # noqa: N802
            parent_box["inst"] = self

        def render(self) -> object:
            return create_element(Child, {"ref": child_ref})

    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        with act(flush=root.flush):
            root.render(create_element(Parent))
        with act(flush=root.flush):
            parent_box["inst"].force_update()
            cast(Any, child_ref.current).force_update()
    finally:
        set_act_environment_enabled(False)


def test_does_not_update_one_component_twice_in_a_batch_6371() -> None:
    callbacks: list[Any] = []

    def emit_change() -> None:
        for c in callbacks:
            c()

    class EmitsChangeOnUnmount(Component):
        def componentWillUnmount(self) -> None:  # noqa: N802
            emit_change()

        def render(self) -> object:
            return None

    class ForceUpdatesOnChange(Component):
        def componentDidMount(self) -> None:  # noqa: N802
            self.on_change = lambda: self.force_update()
            self.on_change()
            callbacks.append(self.on_change)

        def componentWillUnmount(self) -> None:  # noqa: N802
            nonlocal callbacks
            callbacks = [c for c in callbacks if c is not self.on_change]

        def render(self) -> object:
            return create_element("div", {"key": str(random.random())})

    class App(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self._state = {"showChild": True}

        def componentDidMount(self) -> None:  # noqa: N802
            self.set_state({"showChild": False})

        def render(self) -> object:
            children: list[object] = [create_element(ForceUpdatesOnChange)]
            if self.state["showChild"]:
                children.append(create_element(EmitsChangeOnUnmount))
            return create_element("div", {"children": tuple(children)})

    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        with act(flush=root.flush):
            root.render(create_element(App))
    finally:
        set_act_environment_enabled(False)
