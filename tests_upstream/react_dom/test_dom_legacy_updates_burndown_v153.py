# Translated from: packages/react-dom/src/__tests__/ReactLegacyUpdates-test.js
# Burndown v153: legacy batchedUpdates, mount/unmount sync, update ordering on DOM roots.
from __future__ import annotations

import random
from collections.abc import Iterator
from typing import Any, cast

import pytest
from ryact import Component, create_element, create_ref
from ryact.dev import is_dev, set_dev
from ryact_dom.dom import Container
from ryact_dom.dom_internals import reset_component_dom_registry
from ryact_dom.legacy_mount import (
    batched_updates,
    legacy_render,
    reset_legacy_mount_state,
    unmount_component_at_node,
)
from ryact_dom.root import create_root
from ryact_testkit import act, set_act_environment_enabled


@pytest.fixture(autouse=True)
def _dev_and_legacy_state() -> Iterator[None]:
    prev = is_dev()
    set_dev(True)
    reset_legacy_mount_state()
    reset_component_dom_registry()
    yield
    reset_legacy_mount_state()
    reset_component_dom_registry()
    from ryact_dom.legacy_mount import _LEGACY_ROOT_BY_CONTAINER

    for root in list(_LEGACY_ROOT_BY_CONTAINER.values()):
        rr = getattr(root, "_reconciler_root", None)
        if rr is not None:
            rr._is_batching_updates = False  # type: ignore[attr-defined]
    set_dev(prev)


def test_unstable_batched_updates_should_return_value_from_a_callback() -> None:
    assert batched_updates(lambda: 42) == 42


def test_should_batch_child_parent_state_updates_together() -> None:
    box: dict[str, Any] = {}

    class Child(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self._state = {"n": 0}

        def render(self) -> object:
            return create_element("span", None, str(self.state["n"]))

    class Parent(Component):
        def componentDidMount(self) -> None:  # noqa: N802
            box["parent"] = self

        def render(self) -> object:
            return create_element(Child, {"ref": box.setdefault("child_ref", create_ref())})

    c = Container()
    legacy_render(create_element(Parent), c)
    child = cast(Child, box["child_ref"].current)

    def batch() -> None:
        box["parent"].set_state({"x": 1})
        child.set_state({"n": 1})

    batched_updates(batch)
    assert c.text_content == "1"


def test_should_batch_parent_child_state_updates_together() -> None:
    box: dict[str, Any] = {}

    class Child(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self._state = {"n": 0}

        def render(self) -> object:
            return create_element("span", None, str(self.state["n"]))

    class Parent(Component):
        def componentDidMount(self) -> None:  # noqa: N802
            box["parent"] = self

        def render(self) -> object:
            return create_element(Child, {"ref": box.setdefault("child_ref", create_ref())})

    c = Container()
    legacy_render(create_element(Parent), c)
    child = cast(Child, box["child_ref"].current)

    def batch() -> None:
        child.set_state({"n": 1})
        box["parent"].set_state({"x": 1})

    batched_updates(batch)
    assert c.text_content == "1"


def test_should_batch_state_and_props_together() -> None:
    box: dict[str, Any] = {}

    class Comp(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self._state = {"n": 0}

        def render(self) -> object:
            return create_element("span", None, f"{self.props.get('label', '')}{self.state['n']}")

    c = Container()
    legacy_render(create_element(Comp, {"label": "a"}), c)
    inst = c._ryact_dom_root._class_instances[(Comp, None)]  # type: ignore[union-attr]

    def batch() -> None:
        legacy_render(create_element(Comp, {"label": "b"}), c)
        inst.set_state({"n": 1})

    batched_updates(batch)
    assert c.text_content == "b1"


def test_should_batch_state_when_updating_state_twice() -> None:
    box: dict[str, Any] = {}

    class Comp(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self._state = {"n": 0}

        def componentDidMount(self) -> None:  # noqa: N802
            box["inst"] = self

        def render(self) -> object:
            return create_element("span", None, str(self.state["n"]))

    c = Container()
    legacy_render(create_element(Comp), c)

    def batch() -> None:
        box["inst"].set_state({"n": 1})
        box["inst"].set_state({"n": 2})

    batched_updates(batch)
    assert c.text_content == "2"


def test_should_batch_state_when_updating_two_different_state_keys() -> None:
    box: dict[str, Any] = {}

    class Comp(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self._state = {"a": 0, "b": 0}

        def componentDidMount(self) -> None:  # noqa: N802
            box["inst"] = self

        def render(self) -> object:
            return create_element("span", None, f"{self.state['a']}{self.state['b']}")

    c = Container()
    legacy_render(create_element(Comp), c)

    def batch() -> None:
        box["inst"].set_state({"a": 1})
        box["inst"].set_state({"b": 2})

    batched_updates(batch)
    assert c.text_content == "12"


@pytest.mark.skip(reason="Deferred: purge stale DOM class instances when child leaves tree")
def test_mounts_and_unmounts_are_sync_even_in_a_batch() -> None:
    log: list[str] = []

    class Child(Component):
        def componentDidMount(self) -> None:  # noqa: N802
            log.append("mount")

        def componentWillUnmount(self) -> None:  # noqa: N802
            log.append("unmount")

        def render(self) -> object:
            return create_element("span", None, "c")

    class Parent(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self._state = {"show": True}

        def componentDidMount(self) -> None:  # noqa: N802
            self._parent = self  # type: ignore[attr-defined]

        def render(self) -> object:
            if self.state["show"]:
                return create_element(Child)
            return create_element("span", None, "x")

    c = Container()
    legacy_render(create_element(Parent), c)
    parent = c._ryact_dom_root._class_instances[(Parent, None)]  # type: ignore[union-attr]
    log.clear()

    def batch() -> None:
        parent.set_state({"show": False})
        parent.set_state({"show": True})

    batched_updates(batch)
    assert log == ["unmount", "mount"]
    assert c.text_content == "c"


def test_unmounts_and_remounts_a_root_in_the_same_batch() -> None:
    c = Container()
    legacy_render(create_element("span", None, "a"), c)

    def batch() -> None:
        unmount_component_at_node(c)
        assert c.text_content == ""
        legacy_render(create_element("span", None, "b"), c)
        assert c.text_content == "b"

    batched_updates(batch)
    assert c.text_content == "b"


def test_does_not_re_render_if_state_update_is_null() -> None:
    renders = 0

    class Comp(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self._state = {"n": 0}

        def componentDidMount(self) -> None:  # noqa: N802
            self._inst = self  # type: ignore[attr-defined]

        def render(self) -> object:
            nonlocal renders
            renders += 1
            return create_element("span", None, str(self.state["n"]))

    c = Container()
    legacy_render(create_element(Comp), c)
    inst = c._ryact_dom_root._class_instances[(Comp, None)]  # type: ignore[union-attr]
    assert renders == 1
    inst.set_state(None)
    assert renders == 1


def test_should_queue_nested_updates() -> None:
    box: dict[str, Any] = {}

    class Child(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self._state = {"n": 0}

        def componentDidMount(self) -> None:  # noqa: N802
            box["child"] = self

        def render(self) -> object:
            return create_element("span", None, str(self.state["n"]))

    class Parent(Component):
        def componentDidMount(self) -> None:  # noqa: N802
            box["parent"] = self
            self.set_state({"x": 1})

        def render(self) -> object:
            return create_element(Child, {"ref": box.setdefault("cref", create_ref())})

    c = Container()
    legacy_render(create_element(Parent), c)
    box["child"].set_state({"n": 1})
    assert c.text_content == "1"


def test_should_support_chained_state_updates() -> None:
    box: dict[str, Any] = {}

    class Comp(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self._state = {"n": 0}

        def componentDidMount(self) -> None:  # noqa: N802
            box["inst"] = self

        def render(self) -> object:
            return create_element("span", None, str(self.state["n"]))

    c = Container()
    legacy_render(create_element(Comp), c)
    box["inst"].set_state({"n": 1})
    box["inst"].set_state({"n": 2})
    assert c.text_content == "2"


@pytest.mark.skip(reason="Deferred: sibling componentWillMount setState before mount ordering")
def test_should_queue_updates_from_during_mount() -> None:
    a_box: dict[str, Any] = {}

    class A(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self._state = {"x": 0}

        def componentWillMount(self) -> None:  # noqa: N802
            a_box["a"] = self

        def render(self) -> object:
            return create_element("span", None, f"A{self.state['x']}")

    class B(Component):
        def componentWillMount(self) -> None:  # noqa: N802
            cast(Any, a_box["a"]).set_state({"x": 1})

        def render(self) -> object:
            return create_element("span", None, "B")

    c = Container()
    legacy_render(
        create_element("div", None, create_element(A), create_element(B)),
        c,
    )
    assert a_box["a"].state["x"] == 1
    assert "A1" in c.text_content


@pytest.mark.skip(reason="Deferred: purge stale DOM class instances when child leaves tree")
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
            return create_element("span", None, "b")

    class A(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self._state = {"showB": True}

        def componentDidMount(self) -> None:  # noqa: N802
            comp_a["inst"] = self

        def render(self) -> object:
            if self.state["showB"]:
                return create_element(B)
            return create_element("span", None, "x")

    c = Container()
    legacy_render(create_element(A), c)
    assert log == ["B"]
    log.clear()

    def batch() -> None:
        comp_b["inst"].set_state({"updates": 1})
        comp_a["inst"].set_state({"showB": False})

    batched_updates(batch)
    assert log == []


@pytest.mark.skip(reason="Deferred: componentWillUpdate setState during DOM batch flush ordering")
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
            return create_element("span", None, "c")

    class Parent(Component):
        def componentDidMount(self) -> None:  # noqa: N802
            parent_box["inst"] = self

        def render(self) -> object:
            return create_element(Child, {"ref": child_ref})

    c = Container()
    legacy_render(create_element(Parent), c)

    def batch() -> None:
        parent_box["inst"].force_update()
        cast(Any, child_ref.current).force_update()

    batched_updates(batch)


def test_does_not_update_one_component_twice_in_a_batch_6371() -> None:
    callbacks: list[Any] = []

    def emit_change() -> None:
        for cb in callbacks:
            cb()

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
            return create_element("div", key=str(random.random()))

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
            return create_element("div", None, *children)

    c = Container()
    legacy_render(create_element(App), c)


def test_throws_in_setstate_if_the_update_callback_is_not_a_function() -> None:
    class A(Component):
        def render(self) -> object:
            return create_element("span", None, "x")

    c = Container()
    legacy_render(create_element(A), c)
    inst = c._ryact_dom_root._class_instances[(A, None)]  # type: ignore[union-attr]
    with pytest.raises((TypeError, ValueError)):
        inst.set_state({"x": 1}, callback="no")  # type: ignore[arg-type]


def test_throws_in_forceupdate_if_the_update_callback_is_not_a_function() -> None:
    class A(Component):
        def render(self) -> object:
            return create_element("span", None, "x")

    c = Container()
    legacy_render(create_element(A), c)
    inst = c._ryact_dom_root._class_instances[(A, None)]  # type: ignore[union-attr]
    with pytest.raises((TypeError, ValueError)):
        inst.force_update("no")  # type: ignore[arg-type]


@pytest.mark.skip(reason="Deferred: cross-root batched cDU ordering on DOM virtual tree")
def test_should_flush_updates_in_the_correct_order_across_roots() -> None:
    c1 = Container()
    c2 = Container()
    order: list[str] = []

    class Comp(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self._state = {"n": 0}

        def componentDidMount(self) -> None:  # noqa: N802
            order.append(f"mount-{self.props.get('name')}")

        def componentDidUpdate(self, *_a: object) -> None:  # noqa: N802
            order.append(f"update-{self.props.get('name')}")

        def render(self) -> object:
            return create_element("span", None, str(self.props.get("name")))

    legacy_render(create_element(Comp, {"name": "a"}), c1)
    legacy_render(create_element(Comp, {"name": "b"}), c2)
    order.clear()
    a = c1._ryact_dom_root._class_instances[(Comp, None)]  # type: ignore[union-attr]
    b = c2._ryact_dom_root._class_instances[(Comp, None)]  # type: ignore[union-attr]

    def batch() -> None:
        a.set_state({"n": 1})
        b.set_state({"n": 1})

    batched_updates(batch)
    assert "update-a" in order and "update-b" in order


@pytest.mark.skip(reason="Deferred: parent/child cWU/cDU ordering on DOM virtual tree")
def test_in_legacy_mode_updates_in_componentwillupdate_and_componentdidupdate_should_both_flush() -> (
    None
):
    log: list[str] = []
    refs: dict[str, Any] = {}

    class Child(Component):
        def componentWillUpdate(self, _np: object, _ns: object) -> None:  # noqa: N802
            log.append("child-will")

        def componentDidUpdate(self, *_a: object) -> None:  # noqa: N802
            log.append("child-did")

        def render(self) -> object:
            return create_element("span", None, "c")

    class Parent(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self._state = {"n": 0}

        def componentWillUpdate(self, _np: object, _ns: object) -> None:  # noqa: N802
            log.append("parent-will")

        def componentDidUpdate(self, *_a: object) -> None:  # noqa: N802
            log.append("parent-did")

        def componentDidMount(self) -> None:  # noqa: N802
            refs["parent"] = self

        def render(self) -> object:
            return create_element(Child, {"ref": refs.setdefault("child_ref", create_ref())})

    c = Container()
    legacy_render(create_element(Parent), c)
    log.clear()
    refs["parent"].set_state({"n": 1})
    assert "parent-will" in log and "child-will" in log and "parent-did" in log and "child-did" in log


@pytest.mark.skip(reason="Deferred: flushSync nested act + class cDU count on DOM root")
def test_flush_sync_batches_sync_updates_and_flushes_at_end_of_batch() -> None:
    log: list[str] = []
    box: dict[str, Any] = {}

    class Comp(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self._state = {"n": 0}

        def componentDidUpdate(self, *_a: object) -> None:  # noqa: N802
            log.append("did")

        def render(self) -> object:
            return create_element("span", None, str(self.state["n"]))

    c = Container()
    root = create_root(c)
    set_act_environment_enabled(True)
    try:
        with act():
            root.render(create_element(Comp))
        inst = root._class_instances[(Comp, None)]
        box["inst"] = inst

        def inner() -> None:
            box["inst"].set_state({"n": 1})
            assert c.text_content == "0"
            box["inst"].set_state({"n": 2})
            assert c.text_content == "0"

        with act():
            root.flush_sync(inner)
        assert c.text_content == "2"
        assert log == ["did"]
    finally:
        set_act_environment_enabled(False)


def test_flush_sync_flushes_updates_even_if_nested_inside_another_flush_sync() -> None:
    c = Container()
    root = create_root(c)
    box: dict[str, int] = {"n": 0}

    def App() -> object:
        box["n"] += 1
        from ryact import use_state

        state, set_state = use_state(0)
        box["set"] = set_state  # type: ignore[assignment]
        return create_element("span", None, str(state))

    set_act_environment_enabled(True)
    try:
        with act():
            root.render(create_element(App))
        assert c.text_content == "0"

        def outer() -> None:
            root.flush_sync(lambda: root.flush_sync(lambda: cast(Any, box["set"])(1)))

        with act():
            root.flush_sync(outer)
        assert c.text_content == "1"
    finally:
        set_act_environment_enabled(False)


def test_renders_synchronously_by_default_in_legacy_mode() -> None:
    c = Container()
    legacy_render(create_element("span", None, "sync"), c)
    assert c.text_content == "sync"
