# Translated from:
# - packages/react-dom/src/__tests__/ReactLegacyUpdates-test.js
# - packages/react-dom/src/__tests__/ReactDOMLegacyFiber-test.js (warnings / findDOMNode)
# Burndown v155: legacy mount queue, cWU/cDU ordering, batched guards, fiber warnings.
from __future__ import annotations

from collections.abc import Iterator
from typing import Any, cast

import pytest
from ryact import Children, Component, create_element, create_ref, fragment
from ryact.dev import is_dev, set_dev
from ryact_dom.dom import Container, ElementNode
from ryact_dom.dom_internals import find_dom_node, reset_component_dom_registry
from ryact_dom.legacy_mount import (
    batched_updates,
    legacy_render,
    reset_legacy_mount_state,
)
from ryact_testkit import WarningCapture


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


# --- ReactLegacyUpdates ---


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


def test_calls_componentwillreceiveprops_setstate_callback_properly() -> None:
    log: list[str] = []

    class A(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self._state = {"x": props.get("x")}

        def UNSAFE_componentWillReceiveProps(self, next_props: dict[str, Any]) -> None:  # noqa: N802
            new_x = next_props["x"]

            def cb() -> None:
                assert self.state["x"] == new_x
                log.append("Callback")

            self.set_state({"x": new_x}, callback=cb)

        def render(self) -> object:
            return create_element("span", None, str(self.state["x"]))

    c = Container()
    legacy_render(create_element(A, {"x": 1}), c)
    assert log == []
    legacy_render(create_element(A, {"x": 2}), c)
    assert log == ["Callback"]


def test_should_not_reconcile_children_passed_via_props() -> None:
    log: list[str] = []

    class Bottom(Component):
        def render(self) -> object:
            log.append("Bottom")
            return None

    bottom_el = create_element(Bottom)

    class Middle(Component):
        def componentDidMount(self) -> None:  # noqa: N802
            self.force_update()

        def render(self) -> object:
            log.append("Middle")
            return Children.only(self.props["children"])

    class Top(Component):
        def render(self) -> object:
            return create_element(Middle, None, bottom_el)

    c = Container()
    legacy_render(create_element(Top), c)
    assert log == ["Middle", "Bottom", "Middle"]


def test_handles_reentrant_mounting_in_synchronous_mode() -> None:
    log: list[str] = []
    on_change_called = {"v": False}
    props_box: dict[str, Any] = {"text": "hello", "rendered": False}

    class Editor(Component):
        def componentDidMount(self) -> None:  # noqa: N802
            log.append("Mount")
            if not self.props["rendered"]:
                cast(Any, self.props["onChange"])({"rendered": True})

        def render(self) -> object:
            return create_element("span", None, str(self.props["text"]))

    c = Container()

    def render_editor() -> None:
        def on_change(new_props: dict[str, Any]) -> None:
            on_change_called["v"] = True
            props_box.update(new_props)
            render_editor()

        legacy_render(
            create_element(
                Editor,
                {
                    "onChange": on_change,
                    "text": props_box["text"],
                    "rendered": props_box["rendered"],
                },
            ),
            c,
        )

    render_editor()
    assert log == ["Mount"]
    props_box["text"] = "goodbye"
    render_editor()
    assert log == ["Mount"]
    assert c.text_content == "goodbye"
    assert on_change_called["v"]


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
            return create_element(
                "div",
                None,
                self.props["children"],
            )

    class Child(Component):
        displayName = "Child"

        def componentWillUpdate(self, _np: object, _ns: object) -> None:  # noqa: N802
            _mixin_will(self)

        def componentDidUpdate(self, *_args: object) -> None:  # noqa: N802
            _mixin_did(self)

        def render(self) -> object:
            return create_element("span", None, "c")

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
                    "div",
                    {"style": {"display": display}},
                    child,
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

    def trigger_update(comp: Component) -> None:
        comp.set_state({"x": 1})

    def test_updates(components: list[Component], desired_will: list[str], desired_did: list[str]) -> None:
        for comp in components:
            trigger_update(comp)
        expect_updates(desired_will, desired_did)
        for comp in reversed(components):
            trigger_update(comp)
        expect_updates(desired_will, desired_did)

    c = Container()
    legacy_render(create_element(App), c)
    switcher = cast(Component, refs["switcherRef"].current)
    box_inst = cast(Component, refs["box"].current)
    child_inst = cast(Component, refs["child"].current)

    test_updates([box_inst, switcher], ["Switcher", "Box"], ["Box", "Switcher"])
    test_updates([child_inst, box_inst], ["Box", "Child"], ["Box", "Child"])
    test_updates(
        [child_inst, switcher],
        ["Switcher", "Box", "Child"],
        ["Box", "Switcher", "Child"],
    )


# --- ReactDOMLegacyFiber ---


def test_should_warn_for_non_functional_event_listeners() -> None:
    c = Container()
    with WarningCapture() as cap:
        legacy_render(create_element("div", {"onClick": "not-a-function"}), c)
    assert any("listener to be a function" in str(r.message) for r in cap.records)


def test_should_warn_when_replacing_a_container_which_was_manually_updated_outside_of_react() -> None:
    c = Container()
    legacy_render(create_element("div", None, "hi"), c)
    c.root.append_child(ElementNode(tag="p"))
    with WarningCapture() as cap:
        legacy_render(create_element("div", None, "bye"), c)
    msgs = [str(r.message) for r in cap.records]
    assert any("updated without using React" in m for m in msgs)
    assert any("Replacing React-rendered children" in m for m in msgs)


def test_finds_the_first_child_even_when_first_child_renders_null() -> None:
    class Comp(Component):
        def render(self) -> object:
            return fragment(None, create_element("span", None, "x"))

    c = Container()
    inst_ref = create_ref()
    legacy_render(create_element(Comp, {"ref": inst_ref}), c)
    node = find_dom_node(cast(Comp, inst_ref.current))
    assert isinstance(node, ElementNode)
    assert node.tag.lower() == "span"


def test_should_render_a_text_component_with_a_text_dom_node_on_the_same_document_as_the_container() -> None:
    class TextComp(Component):
        def render(self) -> object:
            return "hello"

    c = Container()
    legacy_render(create_element(TextComp), c)
    assert c.text_content == "hello"


def test_should_not_update_event_handlers_until_commit() -> None:
    log: list[str] = []

    def handler(_evt: object = None) -> None:
        log.append("click")

    class Comp(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self._state = {"on": handler}

        def render(self) -> object:
            return create_element("div", {"onClick": self.state["on"]})

    c = Container()
    legacy_render(create_element(Comp), c)
    div = c.root.children[0]
    assert isinstance(div, ElementNode)
    assert not log
    div.dispatch_event("click")
    assert log == ["click"]
    inst = c._ryact_dom_root._class_instances[(Comp, None)]  # type: ignore[union-attr]

    def new_handler(_evt: object = None) -> None:
        log.append("new")

    batched_updates(lambda: inst.set_state({"on": new_handler}))
    assert log == ["click"]
    div.dispatch_event("click")
    assert log == ["click", "new"]
