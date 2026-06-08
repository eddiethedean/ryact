# Translated from: packages/react-dom/src/__tests__/ReactLegacyUpdates-test.js
# Burndown v181: legacy batched mount/unmount sync and deferred update ordering on DOM.
from __future__ import annotations

from collections.abc import Iterator
from typing import Any, cast

import pytest
from ryact import Component, create_element, create_ref
from ryact.dev import is_dev, set_dev
from ryact_dom.dom import Container
from ryact_dom.dom_internals import reset_component_dom_registry
from ryact_dom.legacy_mount import batched_updates, legacy_render, reset_legacy_mount_state
from ryact_dom.root import _dom_class_instance_cache_key
from ryact_testkit import set_act_environment_enabled


@pytest.fixture(autouse=True)
def _dev_and_legacy_state() -> Iterator[None]:
    prev = is_dev()
    set_dev(True)
    reset_legacy_mount_state()
    reset_component_dom_registry()
    set_act_environment_enabled(True)
    yield
    reset_legacy_mount_state()
    reset_component_dom_registry()
    set_act_environment_enabled(False)
    set_dev(prev)


def _root_class_instance(root: Any, cls: type[Component], *, slot: int = 0) -> Component:
    key = _dom_class_instance_cache_key(cls, None, ("host", ()), slot)
    return cast(Component, root._class_instances[key])


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

        def render(self) -> object:
            if self.state["show"]:
                return create_element(Child)
            return create_element("span", None, "x")

    c = Container()
    parent = legacy_render(create_element(Parent), c)
    log.clear()

    def batch() -> None:
        parent.set_state({"show": False})
        parent.set_state({"show": True})

    batched_updates(batch)
    assert log == ["unmount", "mount"]
    assert c.text_content == "c"


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
    a = _root_class_instance(c1._ryact_dom_root, Comp)
    b = _root_class_instance(c2._ryact_dom_root, Comp)

    def batch() -> None:
        a.set_state({"n": 1})
        b.set_state({"n": 1})

    batched_updates(batch)
    assert "update-a" in order and "update-b" in order


def test_in_legacy_mode_updates_in_componentwillupdate_and_componentdidupdate_should_both_flush() -> None:
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
