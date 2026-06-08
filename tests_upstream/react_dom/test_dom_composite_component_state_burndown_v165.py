# Translated from: packages/react-dom/src/__tests__/ReactCompositeComponentState-test.js
# Burndown v165: class component state updates and lifecycle ordering.
from __future__ import annotations

from collections.abc import Iterator
from typing import Any, cast

import pytest
from ryact import Component, create_element
from ryact.dev import is_dev, set_dev
from ryact_dom.dom import Container, ElementNode, TextNode
from ryact_dom.legacy_mount import batched_updates, legacy_render, reset_legacy_mount_state
from ryact_dom.root import create_root
from ryact_testkit import WarningCapture


@pytest.fixture(autouse=True)
def _dev_and_reset() -> Iterator[None]:
    prev = is_dev()
    set_dev(True)
    reset_legacy_mount_state()
    yield
    reset_legacy_mount_state()
    set_dev(prev)


def _text(container: Container) -> str:
    def walk(node: object) -> str:
        if isinstance(node, TextNode):
            return node.text
        if isinstance(node, ElementNode):
            return "".join(walk(ch) for ch in node.children)
        return ""

    return "".join(walk(ch) for ch in container.root.children)


def test_should_support_setting_state() -> None:
    log: list[tuple[str, str | None]] = []

    class TestComponent(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self._state = {"color": "red"}
            self._peek("getInitialState", None)

        def _peek(self, label: str, state_color: str | None = None) -> None:
            listener = self.props.get("stateListener")
            if callable(listener):
                color = state_color
                if color is None and isinstance(self._state, dict):
                    color = cast(str | None, self._state.get("color"))
                listener(label, color)

        def set_favorite_color(self, next_color: str) -> None:
            self.set_state({"color": next_color}, callback=lambda: self._peek("setFavoriteColor"))

        def render(self) -> object:
            self._peek("render")
            return create_element("span", None, str(self.state.get("color", "")))

        def UNSAFE_componentWillMount(self) -> None:  # noqa: N802
            self._peek("componentWillMount-start")
            self.set_state(lambda _st: self._peek("before-setState-sunrise", "red"))
            self.set_state({"color": "sunrise"}, callback=lambda: self._peek("setState-sunrise"))
            self.set_state(lambda st: self._peek("after-setState-sunrise", cast(dict, st).get("color")))
            self._peek("componentWillMount-after-sunrise")
            self.set_state({"color": "orange"}, callback=lambda: self._peek("setState-orange"))
            self.set_state(lambda st: self._peek("after-setState-orange", cast(dict, st).get("color")))
            self._peek("componentWillMount-end")

        def componentDidMount(self) -> None:  # noqa: N802
            self._peek("componentDidMount-start")
            self.set_state({"color": "yellow"}, callback=lambda: self._peek("setState-yellow"))
            self._peek("componentDidMount-end")

        def UNSAFE_componentWillReceiveProps(self, new_props: object) -> None:  # noqa: N802
            self._peek("componentWillReceiveProps-start")
            np = cast(dict[str, Any], new_props)
            if np.get("nextColor"):
                self.set_state(
                    lambda st: (
                        self._peek("before-setState-receiveProps", cast(dict, st).get("color")),
                        {"color": np["nextColor"]},
                    )[1]
                )
                self.replace_state({"color": None})
                self.set_state(
                    lambda st: (
                        self._peek("before-setState-again-receiveProps", cast(dict, st).get("color")),
                        {"color": np["nextColor"]},
                    )[1],
                    callback=lambda: self._peek("setState-receiveProps"),
                )
                self.set_state(lambda st: self._peek("after-setState-receiveProps", cast(dict, st).get("color")))
            self._peek("componentWillReceiveProps-end")

        def shouldComponentUpdate(self, _np: object, next_state: object) -> bool:  # noqa: N802
            ns = cast(dict[str, Any], next_state)
            self._peek("shouldComponentUpdate-currentState")
            self._peek("shouldComponentUpdate-nextState", ns.get("color"))
            return True

        def UNSAFE_componentWillUpdate(self, _np: object, next_state: object) -> None:  # noqa: N802
            ns = cast(dict[str, Any], next_state)
            self._peek("componentWillUpdate-currentState")
            self._peek("componentWillUpdate-nextState", ns.get("color"))

        def componentDidUpdate(self, _prev_props: object, prev_state: object) -> None:  # noqa: N802
            ps = cast(dict[str, Any], prev_state)
            self._peek("componentDidUpdate-currentState")
            self._peek("componentDidUpdate-prevState", ps.get("color"))

        def componentWillUnmount(self) -> None:  # noqa: N802
            self._peek("componentWillUnmount")

    container = Container()
    inst_box: dict[str, TestComponent] = {}

    def listener(label: str, color: str | None) -> None:
        log.append((label, color))

    class Tracked(TestComponent):
        def componentDidMount(self) -> None:  # noqa: N802
            inst_box["inst"] = self
            super().componentDidMount()

    legacy_render(create_element(Tracked, {"stateListener": listener}), container)
    inst = inst_box["inst"]

    legacy_render(
        create_element(Tracked, {"stateListener": listener, "nextColor": "green"}),
        container,
        callback=lambda: inst._peek("setProps"),
    )
    inst.set_favorite_color("blue")
    inst.force_update(callback=lambda: inst._peek("forceUpdate"))
    legacy_render(None, container)

    labels = [a for a, _ in log]
    assert labels[0:4] == [
        "getInitialState",
        "componentWillMount-start",
        "componentWillMount-after-sunrise",
        "componentWillMount-end",
    ]
    assert "before-setState-sunrise" in labels
    assert "after-setState-sunrise" in labels
    assert "render" in labels
    assert "componentDidMount-start" in labels
    assert "componentWillUnmount" in labels
    assert log[-1] == ("componentWillUnmount", "blue")


def test_should_call_component_did_update_of_children_first() -> None:
    ops: list[str] = []
    box: dict[str, Any] = {}

    class Child(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self._state = {"bar": False}

        def componentDidMount(self) -> None:  # noqa: N802
            box["child"] = self

        def componentDidUpdate(self, *_a: object) -> None:  # noqa: N802
            ops.append("child did update")

        def render(self) -> object:
            return create_element("span")

    class Intermediate(Component):
        def shouldComponentUpdate(self, *_a: object) -> bool:  # noqa: N802
            return bool(box.get("should_update", True))

        def render(self) -> object:
            return create_element(Child)

    class Parent(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self._state = {"foo": False}

        def componentDidMount(self) -> None:  # noqa: N802
            box["parent"] = self

        def componentDidUpdate(self, *_a: object) -> None:  # noqa: N802
            ops.append("parent did update")

        def render(self) -> object:
            return create_element(Intermediate)

    container = Container()
    legacy_render(create_element(Parent), container)

    def batch() -> None:
        cast(Parent, box["parent"]).set_state({"foo": True})
        cast(Child, box["child"]).set_state({"bar": True})

    batched_updates(batch)
    assert ops == ["child did update", "parent did update"]

    ops.clear()
    box["should_update"] = False
    batched_updates(batch)
    assert ops == ["child did update", "parent did update"]


def test_should_batch_unmounts() -> None:
    outer_box: dict[str, Component] = {}

    class Inner(Component):
        def render(self) -> object:
            return create_element("span")

        def componentWillUnmount(self) -> None:  # noqa: N802
            outer_box["outer"].set_state({"showInner": False})

    class Outer(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self._state = {"showInner": True}

        def render(self) -> object:
            return create_element("div", None, create_element(Inner) if self.state["showInner"] else None)

    container = Container()
    legacy_render(create_element(Outer), container)
    outer_box["outer"] = cast(
        Component,
        next(iter(container._ryact_dom_root._class_instances.values())),  # type: ignore[attr-defined]
    )
    legacy_render(None, container)


def test_should_update_state_when_called_from_child_cwrp() -> None:
    log: list[str] = []
    updated = {"v": False}

    class Parent(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self._state = {"value": "one"}

        def render(self) -> object:
            log.append(f"parent render {self.state['value']}")
            return create_element(Child, {"parent": self, "value": self.state["value"]})

    class Child(Component):
        def UNSAFE_componentWillReceiveProps(self, next_props: object) -> None:  # noqa: N802
            if updated["v"]:
                return
            np = cast(dict[str, Any], next_props)
            log.append(f"child componentWillReceiveProps {np['value']}")
            cast(Parent, np["parent"]).set_state({"value": "two"})
            log.append(f"child componentWillReceiveProps done {np['value']}")
            updated["v"] = True

        def render(self) -> object:
            log.append(f"child render {self.props['value']}")
            return create_element("span", None, str(self.props["value"]))

    container = Container()
    legacy_render(create_element(Parent), container)
    legacy_render(create_element(Parent), container)
    assert log == [
        "parent render one",
        "child render one",
        "parent render one",
        "child componentWillReceiveProps one",
        "child componentWillReceiveProps done one",
        "child render one",
        "parent render two",
        "child render two",
    ]


def test_should_merge_state_when_scu_returns_false() -> None:
    log: list[str] = []

    class Test(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self._state = {"a": 0}

        def render(self) -> object:
            return None

        def shouldComponentUpdate(self, _np: object, next_state: object) -> bool:  # noqa: N802
            ns = cast(dict[str, Any], next_state)
            log.append(f"scu from {sorted(self.state.keys())} to {sorted(ns.keys())}")
            return False

    container = Container()
    root = create_root(container)
    root.render(create_element(Test))
    inst = cast(Test, next(iter(root._class_instances.values())))
    inst.set_state({"b": 0})
    assert log == ["scu from ['a'] to ['a', 'b']"]
    inst.set_state({"c": 0})
    assert log == ["scu from ['a'] to ['a', 'b']", "scu from ['a', 'b'] to ['a', 'b', 'c']"]


def test_should_treat_assigning_to_this_state_inside_cwrp_as_replace_state_with_warning() -> None:
    ops: list[str] = []

    class Test(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self._state = {"step": 1, "extra": True}

        def UNSAFE_componentWillReceiveProps(self, _np: object) -> None:  # noqa: N802
            self.set_state(
                {"step": 2},
                callback=lambda: ops.append(
                    f"callback -- step: {self.state['step']}, extra: {bool(self.state.get('extra'))}"
                ),
            )
            self._state = {"step": 3}

        def render(self) -> object:
            ops.append(f"render -- step: {self.state['step']}, extra: {bool(self.state.get('extra'))}")
            return None

    container = Container()
    legacy_render(create_element(Test), container)
    with WarningCapture() as cap:
        legacy_render(create_element(Test, {"tick": 1}), container)
    assert any("Assigning directly to this.state is deprecated" in str(r.message) for r in cap.records)
    assert ops == [
        "render -- step: 1, extra: True",
        "render -- step: 3, extra: False",
        "callback -- step: 3, extra: False",
    ]
    with WarningCapture() as cap2:
        legacy_render(create_element(Test, {"tick": 2}), container)
    assert not cap2.records


def test_should_treat_assigning_to_this_state_inside_cwm_as_replace_state_with_warning() -> None:
    ops: list[str] = []

    class Test(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self._state = {"step": 1, "extra": True}

        def UNSAFE_componentWillMount(self) -> None:  # noqa: N802
            self.set_state(
                {"step": 2},
                callback=lambda: ops.append(
                    f"callback -- step: {self.state['step']}, extra: {bool(self.state.get('extra'))}"
                ),
            )
            self._state = {"step": 3}

        def render(self) -> object:
            ops.append(f"render -- step: {self.state['step']}, extra: {bool(self.state.get('extra'))}")
            return None

    container = Container()
    with WarningCapture() as cap:
        legacy_render(create_element(Test), container)
    assert any("Assigning directly to this.state is deprecated" in str(r.message) for r in cap.records)
    assert ops == [
        "render -- step: 3, extra: False",
        "callback -- step: 3, extra: False",
    ]


def test_legacy_mode_should_support_setstate_in_componentwillunmount() -> None:
    subscription: dict[str, Any] = {"fn": None}

    class A(Component):
        def componentWillUnmount(self) -> None:  # noqa: N802
            fn = subscription.get("fn")
            if callable(fn):
                fn()

        def render(self) -> object:
            return create_element("span", None, "A")

    class B(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self._state = {"siblingUnmounted": False}

        def UNSAFE_componentWillMount(self) -> None:  # noqa: N802
            subscription["fn"] = lambda: self.set_state({"siblingUnmounted": True})

        def render(self) -> object:
            suffix = " No Sibling" if self.state["siblingUnmounted"] else ""
            return create_element("span", None, "B" + suffix)

    container = Container()
    legacy_render(create_element("div", None, create_element(A), create_element(B)), container)
    assert _text(container) == "AB"
    legacy_render(create_element("div", None, create_element(B)), container)
    assert _text(container) == "B No Sibling"


def test_should_not_support_setstate_in_componentwillunmount() -> None:
    subscription: dict[str, Any] = {"fn": None}

    class A(Component):
        def componentWillUnmount(self) -> None:  # noqa: N802
            fn = subscription.get("fn")
            if callable(fn):
                fn()

        def render(self) -> object:
            return create_element("span", None, "A")

    class B(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self._state = {"siblingUnmounted": False}

        def UNSAFE_componentWillMount(self) -> None:  # noqa: N802
            subscription["fn"] = lambda: self.set_state({"siblingUnmounted": True})

        def render(self) -> object:
            suffix = " No Sibling" if self.state["siblingUnmounted"] else ""
            return create_element("span", None, "B" + suffix)

    container = Container()
    root = create_root(container)
    root.render(create_element("div", None, create_element(A), create_element(B)))
    assert _text(container) == "AB"
    root.render(create_element("div", None, create_element(B)))
    assert _text(container) == "B"
