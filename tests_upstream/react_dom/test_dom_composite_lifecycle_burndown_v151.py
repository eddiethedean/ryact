# Translated from:
# - packages/react-dom/src/__tests__/ReactComponent-test.js
# - packages/react-dom/src/__tests__/ReactComponentLifeCycle-test.js
# - packages/react-dom/src/__tests__/ReactCompositeComponent-test.js
# - packages/react-dom/src/__tests__/ReactDOMFiber-test.js
# Burndown v151: legacy callbacks, refs, morphing, lifecycle order, portals, effects.
from __future__ import annotations

import copy
from collections.abc import Callable, Iterator
from typing import Any, cast

import pytest
from ryact import Component, create_element, create_portal, create_ref, strict_mode
from ryact.dev import is_dev, set_dev
from ryact.element import LEGACY_REACT_ELEMENT_SENTINEL
from ryact.hooks import use_effect, use_state
from ryact_dom.dom import Container, ElementNode
from ryact_dom.legacy_render import legacy_render
from ryact_dom.root import create_root
from ryact_dom.server import render_to_string
from ryact_testkit import WarningCapture, act, create_noop_root, set_act_environment_enabled


@pytest.fixture(autouse=True)
def _dev_on() -> Iterator[None]:
    prev = is_dev()
    set_dev(True)
    yield
    set_dev(prev)


def _host_child(container: Container) -> ElementNode | None:
    for ch in container.root.children:
        if isinstance(ch, ElementNode):
            return ch
    return None


def _host_tag(container: Container) -> str | None:
    ch = _host_child(container)
    return ch.tagName if ch is not None else None


def test_fires_the_callback_after_a_component_is_rendered_in_legacy_roots() -> None:
    calls: list[int] = []

    def callback() -> None:
        calls.append(1)

    c = Container()
    legacy_render(create_element("div", None), c, callback)
    assert len(calls) == 1
    legacy_render(create_element("div", {"className": "foo"}), c, callback)
    assert len(calls) == 2
    legacy_render(create_element("span", None), c, callback)
    assert len(calls) == 3


def test_should_call_refs_at_the_correct_time() -> None:
    log: list[str] = []

    class Inner(Component):
        def render(self) -> object:
            log.append(f"inner {self.props['id']} render")
            return create_element("div")

        def componentDidMount(self) -> None:  # noqa: N802
            log.append(f"inner {self.props['id']} componentDidMount")

        def componentDidUpdate(self, *_args: object) -> None:  # noqa: N802
            log.append(f"inner {self.props['id']} componentDidUpdate")

        def componentWillUnmount(self) -> None:  # noqa: N802
            log.append(f"inner {self.props['id']} componentWillUnmount")

    class Outer(Component):
        def render(self) -> object:
            return create_element(
                "div",
                {
                    "children": (
                        create_element(
                            Inner,
                            {
                                "key": "i1",
                                "id": 1,
                                "ref": lambda c: log.append(
                                    f"ref 1 got {'instance ' + str(c.props['id']) if c else 'null'}"
                                ),
                            },
                        ),
                        create_element(
                            Inner,
                            {
                                "key": "i2",
                                "id": 2,
                                "ref": lambda c: log.append(
                                    f"ref 2 got {'instance ' + str(c.props['id']) if c else 'null'}"
                                ),
                            },
                        ),
                    ),
                },
            )

        def componentDidMount(self) -> None:  # noqa: N802
            log.append("outer componentDidMount")

        def componentDidUpdate(self, *_args: object) -> None:  # noqa: N802
            log.append("outer componentDidUpdate")

        def componentWillUnmount(self) -> None:  # noqa: N802
            log.append("outer componentWillUnmount")

    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        log.clear()
        log.append("start mount")
        with act(flush=root.flush):
            root.render(create_element(Outer))
        log.append("start update")
        with act(flush=root.flush):
            root.render(create_element(Outer))
        log.append("start unmount")
        with act(flush=root.flush):
            root.render(None)
    finally:
        set_act_environment_enabled(False)

    assert log == [
        "start mount",
        "inner 1 render",
        "inner 2 render",
        "inner 1 componentDidMount",
        "ref 1 got instance 1",
        "inner 2 componentDidMount",
        "ref 2 got instance 2",
        "outer componentDidMount",
        "start update",
        "inner 1 render",
        "inner 2 render",
        "ref 1 got null",
        "inner 1 componentDidUpdate",
        "ref 1 got instance 1",
        "ref 2 got null",
        "inner 2 componentDidUpdate",
        "ref 2 got instance 2",
        "outer componentDidUpdate",
        "start unmount",
        "outer componentWillUnmount",
        "ref 1 got null",
        "inner 1 componentWillUnmount",
        "ref 2 got null",
        "inner 2 componentWillUnmount",
    ]


def test_should_not_have_string_refs_on_unmounted_components() -> None:
    class Child(Component):
        def render(self) -> object:
            return create_element("div")

    class Parent(Component):
        def render(self) -> object:
            return create_element(Child, {"children": create_element("div", {"ref": "test"})})

        def componentDidMount(self) -> None:  # noqa: N802
            assert self.refs.get("test") is None

    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        with act(flush=root.flush):
            root.render(create_element(Parent, {"child": create_element("span")}))
    finally:
        set_act_environment_enabled(False)


def test_should_throw_on_invalid_render_targets_in_legacy_roots() -> None:
    c = Container()
    with pytest.raises(TypeError, match="Target container is not a DOM element"):
        legacy_render(create_element("div", None), [c])  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="Target container is not a DOM element"):
        legacy_render(create_element("div", None), None)  # type: ignore[arg-type]


def test_throws_if_a_legacy_element_is_used_as_a_child() -> None:
    legacy_el = {
        "$$typeof": LEGACY_REACT_ELEMENT_SENTINEL,
        "type": "div",
        "key": None,
        "ref": None,
        "props": {},
    }
    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        with pytest.raises(TypeError, match="older version of React"), act(flush=root.flush):
            root.render(create_element("div", {"children": (legacy_el,)}))
    finally:
        set_act_environment_enabled(False)


def test_throws_if_a_plain_object_even_if_it_is_in_an_owner() -> None:
    class Foo(Component):
        def render(self) -> object:
            children = {"a": create_element("span"), "b": create_element("span"), "c": create_element("span")}
            return create_element("div", {"children": (children,)})

    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        with pytest.raises(TypeError, match="Objects are not valid as a React child"), act(flush=root.flush):
            root.render(create_element(Foo))
    finally:
        set_act_environment_enabled(False)


def test_throws_if_a_plain_object_is_used_as_a_child_when_using_ssr() -> None:
    children = {"x": create_element("span"), "y": create_element("span"), "z": create_element("span")}
    with pytest.raises(TypeError, match="Objects are not valid as a React child"):
        render_to_string(create_element("div", {"children": (children,)}))


def test_throws_if_a_plain_object_even_if_it_is_in_an_owner_when_using_ssr() -> None:
    class Foo(Component):
        def render(self) -> object:
            children = {"a": create_element("span"), "b": create_element("span"), "c": create_element("span")}
            return create_element("div", {"children": (children,)})

    with pytest.raises(TypeError, match="Objects are not valid as a React child"):
        render_to_string(create_element(Foo))


def _polyfill_component(cls: type) -> type:
    cls._ryact_lifecycles_compat_polyfilled = True  # type: ignore[attr-defined]
    return cls


@pytest.mark.skip(reason="Deferred: react-lifecycles-compat polyfill marker slice")
def test_should_not_warn_for_components_with_polyfilled_getderivedstatefromprops() -> None:
    class PolyfilledComponent(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self._state = {}

        @staticmethod
        def getDerivedStateFromProps() -> dict[str, object]:  # noqa: N802
            return {}

        def render(self) -> object:
            return None

    _polyfill_component(PolyfilledComponent)
    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        with WarningCapture() as cap, act(flush=root.flush):
            root.render(create_element(strict_mode, None, create_element(PolyfilledComponent)))
        assert not any(
            "getDerivedStateFromProps() must be declared as a staticmethod" in str(r.message) for r in cap.records
        )
    finally:
        set_act_environment_enabled(False)


def test_should_not_warn_for_components_with_polyfilled_getsnapshotbeforeupdate() -> None:
    class PolyfilledComponent(Component):
        def getSnapshotBeforeUpdate(self, *_a: object) -> None:  # noqa: N802
            return None

        def componentDidUpdate(self, *_a: object) -> None:  # noqa: N802
            return None

        def render(self) -> object:
            return None

    _polyfill_component(PolyfilledComponent)
    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        with WarningCapture() as cap, act(flush=root.flush):
            root.render(create_element(strict_mode, None, create_element(PolyfilledComponent)))
        assert not any("must be declared as a staticmethod" in str(r.message) for r in cap.records)
    finally:
        set_act_environment_enabled(False)


def test_should_call_nested_legacy_lifecycle_methods_in_the_right_order() -> None:
    log: list[str] = []

    def logger(msg: str) -> Callable[..., bool]:
        def _fn(*_a: object, **_k: object) -> bool:
            log.append(msg)
            return True

        return _fn

    class Outer(Component):
        UNSAFE_componentWillMount = logger("outer componentWillMount")  # noqa: N815
        componentDidMount = logger("outer componentDidMount")  # noqa: N815
        UNSAFE_componentWillReceiveProps = logger("outer componentWillReceiveProps")  # noqa: N815
        shouldComponentUpdate = logger("outer shouldComponentUpdate")  # noqa: N815
        UNSAFE_componentWillUpdate = logger("outer componentWillUpdate")  # noqa: N815
        componentDidUpdate = logger("outer componentDidUpdate")  # noqa: N815
        componentWillUnmount = logger("outer componentWillUnmount")  # noqa: N815

        def render(self) -> object:
            return create_element("div", {"children": create_element(Inner, {"x": self.props["x"]})})

    class Inner(Component):
        UNSAFE_componentWillMount = logger("inner componentWillMount")  # noqa: N815
        componentDidMount = logger("inner componentDidMount")  # noqa: N815
        UNSAFE_componentWillReceiveProps = logger("inner componentWillReceiveProps")  # noqa: N815
        shouldComponentUpdate = logger("inner shouldComponentUpdate")  # noqa: N815
        UNSAFE_componentWillUpdate = logger("inner componentWillUpdate")  # noqa: N815
        componentDidUpdate = logger("inner componentDidUpdate")  # noqa: N815
        componentWillUnmount = logger("inner componentWillUnmount")  # noqa: N815

        def render(self) -> object:
            return create_element("span", {"text": str(self.props["x"])})

    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        log.clear()
        with act(flush=root.flush):
            root.render(create_element(Outer, {"x": 1}))
        assert log == [
            "outer componentWillMount",
            "inner componentWillMount",
            "inner componentDidMount",
            "outer componentDidMount",
        ]
        log.clear()
        with act(flush=root.flush):
            root.render(create_element(Outer, {"x": 2}))
        assert log == [
            "outer componentWillReceiveProps",
            "outer shouldComponentUpdate",
            "outer componentWillUpdate",
            "inner componentWillReceiveProps",
            "inner shouldComponentUpdate",
            "inner componentWillUpdate",
            "inner componentDidUpdate",
            "outer componentDidUpdate",
        ]
        log.clear()
        with act(flush=root.flush):
            root.render(None)
        assert log == ["outer componentWillUnmount", "inner componentWillUnmount"]
    finally:
        set_act_environment_enabled(False)


def test_should_call_nested_new_lifecycle_methods_in_the_right_order() -> None:
    log: list[str] = []

    def logger(msg: str) -> Callable[..., bool]:
        def _fn(*_a: object, **_k: object) -> bool:
            log.append(msg)
            return True

        return _fn

    class Outer(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self._state = {}

        @staticmethod
        def getDerivedStateFromProps(_props: object, _prev: object) -> dict[str, object]:  # noqa: N802
            log.append("outer getDerivedStateFromProps")
            return {}

        componentDidMount = logger("outer componentDidMount")  # noqa: N815
        shouldComponentUpdate = logger("outer shouldComponentUpdate")  # noqa: N815
        getSnapshotBeforeUpdate = logger("outer getSnapshotBeforeUpdate")  # noqa: N815
        componentDidUpdate = logger("outer componentDidUpdate")  # noqa: N815
        componentWillUnmount = logger("outer componentWillUnmount")  # noqa: N815

        def render(self) -> object:
            return create_element("div", {"children": create_element(Inner, {"x": self.props["x"]})})

    class Inner(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self._state = {}

        @staticmethod
        def getDerivedStateFromProps(_props: object, _prev: object) -> dict[str, object]:  # noqa: N802
            log.append("inner getDerivedStateFromProps")
            return {}

        componentDidMount = logger("inner componentDidMount")  # noqa: N815
        shouldComponentUpdate = logger("inner shouldComponentUpdate")  # noqa: N815
        getSnapshotBeforeUpdate = logger("inner getSnapshotBeforeUpdate")  # noqa: N815
        componentDidUpdate = logger("inner componentDidUpdate")  # noqa: N815
        componentWillUnmount = logger("inner componentWillUnmount")  # noqa: N815

        def render(self) -> object:
            return create_element("span", {"text": str(self.props["x"])})

    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        log.clear()
        with act(flush=root.flush):
            root.render(create_element(Outer, {"x": 1}))
        assert log == [
            "outer getDerivedStateFromProps",
            "inner getDerivedStateFromProps",
            "inner componentDidMount",
            "outer componentDidMount",
        ]
        log.clear()
        with act(flush=root.flush):
            root.render(create_element(Outer, {"x": 2}))
        assert log == [
            "outer getDerivedStateFromProps",
            "outer shouldComponentUpdate",
            "outer getSnapshotBeforeUpdate",
            "inner getDerivedStateFromProps",
            "inner shouldComponentUpdate",
            "inner getSnapshotBeforeUpdate",
            "inner componentDidUpdate",
            "outer componentDidUpdate",
        ]
        log.clear()
        with act(flush=root.flush):
            root.render(None)
        assert log == ["outer componentWillUnmount", "inner componentWillUnmount"]
    finally:
        set_act_environment_enabled(False)


_GET_INIT = {
    "hasWillMountCompleted": False,
    "hasRenderCompleted": False,
    "hasDidMountCompleted": False,
    "hasWillUnmountCompleted": False,
}
_INIT_RENDER = {**_GET_INIT, "hasWillMountCompleted": True}
_DID_MOUNT = {**_INIT_RENDER, "hasRenderCompleted": True}
_NEXT_RENDER = {**_DID_MOUNT, "hasDidMountCompleted": True}
_WILL_UNMOUNT = {**_NEXT_RENDER, "hasWillUnmountCompleted": False}
_POST_UNMOUNT = {**_WILL_UNMOUNT, "hasWillUnmountCompleted": True}


def test_should_carry_through_each_of_the_phases_of_setup() -> None:
    class LifeCycleComponent(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self._test_journal: dict[str, Any] = {}
            init_state = dict(_GET_INIT)
            self._test_journal["returnedFromGetInitialState"] = copy.deepcopy(init_state)
            self._state = init_state

        def UNSAFE_componentWillMount(self) -> None:  # noqa: N802
            self._test_journal["stateAtStartOfWillMount"] = dict(self.state)
            self.set_state({"hasWillMountCompleted": True})

        def componentDidMount(self) -> None:  # noqa: N802
            self._test_journal["stateAtStartOfDidMount"] = dict(self.state)
            self.set_state({"hasDidMountCompleted": True})

        def render(self) -> object:
            if not self.state["hasRenderCompleted"]:
                self._test_journal["stateInInitialRender"] = dict(self.state)
            else:
                self._test_journal["stateInLaterRender"] = dict(self.state)
            self._state["hasRenderCompleted"] = True
            return create_element("div")

        def componentWillUnmount(self) -> None:  # noqa: N802
            self._test_journal["stateAtStartOfWillUnmount"] = dict(self.state)
            self._state["hasWillUnmountCompleted"] = True

    ref = create_ref()
    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        with act(flush=root.flush):
            root.render(create_element(LifeCycleComponent, {"ref": ref}))
        inst = cast(LifeCycleComponent, ref.current)
        assert inst._test_journal["returnedFromGetInitialState"] == _GET_INIT
        assert inst._test_journal["stateAtStartOfWillMount"] == _GET_INIT
        assert inst._test_journal["stateAtStartOfDidMount"] == _DID_MOUNT
        assert inst._test_journal["stateInInitialRender"] == _INIT_RENDER
        inst.force_update()
        root.flush()
        assert inst._test_journal["stateInLaterRender"] == _NEXT_RENDER
        with act(flush=root.flush):
            root.render(None)
        assert inst._test_journal["stateAtStartOfWillUnmount"] == _WILL_UNMOUNT
        assert inst.state == _POST_UNMOUNT
    finally:
        set_act_environment_enabled(False)


def test_should_fire_ondomready_when_already_in_ondomready() -> None:
    journal: list[str] = []

    class Child(Component):
        def componentDidMount(self) -> None:  # noqa: N802
            journal.append("Child:onDOMReady")

        def render(self) -> object:
            return create_element("div")

    class SwitcherParent(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            journal.append("SwitcherParent:getInitialState")
            self._state = {"showHasOnDOMReadyComponent": False}

        def componentDidMount(self) -> None:  # noqa: N802
            journal.append("SwitcherParent:onDOMReady")
            self.set_state({"showHasOnDOMReadyComponent": True})

        def render(self) -> object:
            if self.state["showHasOnDOMReadyComponent"]:
                return create_element(Child)
            return create_element("div")

    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        with act(flush=root.flush):
            root.render(create_element(SwitcherParent))
        assert journal == [
            "SwitcherParent:getInitialState",
            "SwitcherParent:onDOMReady",
            "Child:onDOMReady",
        ]
    finally:
        set_act_environment_enabled(False)


def test_should_not_reuse_an_instance_when_it_has_been_unmounted() -> None:
    class StatefulComponent(Component):
        def render(self) -> object:
            return create_element("div")

    c = Container()
    root = create_root(c)
    set_act_environment_enabled(True)
    try:
        with act():
            root.render(create_element(StatefulComponent))
        first_id = _host_child(c)._host_reconcile_id if _host_child(c) else None
        with act():
            root.unmount()
        root = create_root(c)
        with act():
            root.render(create_element(StatefulComponent))
        second_id = _host_child(c)._host_reconcile_id if _host_child(c) else None
        assert first_id is not None and second_id is not None
        assert first_id != second_id
    finally:
        set_act_environment_enabled(False)


def test_should_warn_about_deprecated_lifecycles_cwm_cwrp_cwu_if_new_getsnapshotbeforeupdate_is_present() -> None:
    class AllLegacyLifecycles(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self._state = {}

        def getSnapshotBeforeUpdate(self, *_a: object) -> None:  # noqa: N802
            return None

        def componentWillMount(self) -> None:  # noqa: N802
            return None

        def componentWillReceiveProps(self, *_a: object) -> None:  # noqa: N802
            return None

        def componentWillUpdate(self, *_a: object) -> None:  # noqa: N802
            return None

        def componentDidUpdate(self, *_a: object) -> None:  # noqa: N802
            return None

        def render(self) -> object:
            return None

    root = create_noop_root()
    with WarningCapture() as cap:
        root.render(create_element(AllLegacyLifecycles))
        root.flush()
    assert any("Unsafe legacy lifecycles will not be called" in str(r.message) for r in cap.records)
    assert any("getSnapshotBeforeUpdate" in str(r.message) for r in cap.records)


def test_should_not_cache_old_dom_nodes_when_switching_constructors() -> None:
    child_ref = create_ref()

    class ChildUpdates(Component):
        anchor_ref = create_ref()

        def get_anchor(self) -> ElementNode | None:
            ref = self.anchor_ref.current
            return ref if isinstance(ref, ElementNode) else None

        def render(self) -> object:
            if self.props.get("renderAnchor"):
                cls = "anchorClass" if self.props.get("anchorClassOn") else ""
                return create_element("a", {"className": cls, "ref": self.anchor_ref})
            return create_element("b")

    c = Container()
    root = create_root(c)
    set_act_environment_enabled(True)
    try:
        with act():
            root.render(create_element(ChildUpdates, {"ref": child_ref, "renderAnchor": True, "anchorClassOn": False}))
        with act():
            root.render(create_element(ChildUpdates, {"ref": child_ref, "renderAnchor": True, "anchorClassOn": True}))
        with act():
            root.render(create_element(ChildUpdates, {"ref": child_ref, "renderAnchor": False, "anchorClassOn": True}))
        with act():
            root.render(create_element(ChildUpdates, {"ref": child_ref, "renderAnchor": True, "anchorClassOn": False}))
        anchor = cast(ChildUpdates, child_ref.current).get_anchor()
        assert anchor is not None
        assert anchor.props.get("className", "") == ""
    finally:
        set_act_environment_enabled(False)


def test_should_react_to_state_changes_from_callbacks() -> None:
    morph_ref = create_ref()

    class MorphingComponent(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self._state = {"activated": False}
            self.x_ref = create_ref()

        def render(self) -> object:
            if not self.state["activated"]:
                return create_element(
                    "a",
                    {"onClick": self._toggle, "ref": self.x_ref},
                )
            return create_element("b", {"onClick": self._toggle, "ref": self.x_ref})

        def _toggle(self, *_ev: object) -> None:
            self.set_state({"activated": not self.state["activated"]})

    c = Container()
    root = create_root(c)
    set_act_environment_enabled(True)
    try:
        with act():
            root.render(create_element(MorphingComponent, {"ref": morph_ref}))
        assert _host_tag(c) == "A"
        with act():
            cast(ElementNode, _host_child(c)).click()
        assert _host_tag(c) == "B"
    finally:
        set_act_environment_enabled(False)


def test_should_rewire_refs_when_rendering_to_different_child_types() -> None:
    morph_ref = create_ref()

    class MorphingComponent(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self._state = {"activated": False}
            self.x_ref = create_ref()

        def render(self) -> object:
            if not self.state["activated"]:
                return create_element("a", {"ref": self.x_ref})
            return create_element("b", {"ref": self.x_ref})

        def _toggle(self, *_ev: object) -> None:
            self.set_state({"activated": not self.state["activated"]})

    c = Container()
    root = create_root(c)
    set_act_environment_enabled(True)
    try:
        with act():
            root.render(create_element(MorphingComponent, {"ref": morph_ref}))
        assert _host_tag(c) == "A"
        with act():
            cast(MorphingComponent, morph_ref.current)._toggle()
        assert _host_tag(c) == "B"
        with act():
            cast(MorphingComponent, morph_ref.current)._toggle()
        assert _host_tag(c) == "A"
    finally:
        set_act_environment_enabled(False)


def test_should_support_rendering_to_different_child_types_over_time() -> None:
    morph_ref = create_ref()

    class MorphingComponent(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self._state = {"activated": False}
            self.x_ref = create_ref()

        def render(self) -> object:
            if not self.state["activated"]:
                return create_element("a", {"ref": self.x_ref})
            return create_element("b", {"ref": self.x_ref})

        def _toggle(self, *_ev: object) -> None:
            self.set_state({"activated": not self.state["activated"]})

    c = Container()
    root = create_root(c)
    set_act_environment_enabled(True)
    try:
        with act():
            root.render(create_element(MorphingComponent, {"ref": morph_ref}))
        assert _host_tag(c) == "A"
        with act():
            cast(MorphingComponent, morph_ref.current)._toggle()
        assert _host_tag(c) == "B"
        with act():
            cast(MorphingComponent, morph_ref.current)._toggle()
        assert _host_tag(c) == "A"
    finally:
        set_act_environment_enabled(False)


def test_prepares_new_child_before_unmounting_old() -> None:
    log: list[str] = []

    class Spy(Component):
        def UNSAFE_componentWillMount(self) -> None:  # noqa: N802
            log.append(f"{self.props['name']} componentWillMount")

        def render(self) -> object:
            log.append(f"{self.props['name']} render")
            return create_element("div")

        def componentDidMount(self) -> None:  # noqa: N802
            log.append(f"{self.props['name']} componentDidMount")

        def componentWillUnmount(self) -> None:  # noqa: N802
            log.append(f"{self.props['name']} componentWillUnmount")

    class Wrapper(Component):
        def render(self) -> object:
            return create_element(Spy, {"key": self.props["name"], "name": self.props["name"]})

    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        with act(flush=root.flush):
            root.render(create_element(Wrapper, {"name": "A"}))
        assert log == ["A componentWillMount", "A render", "A componentDidMount"]
        log.clear()
        with act(flush=root.flush):
            root.render(create_element(Wrapper, {"name": "B"}))
        assert log == [
            "B componentWillMount",
            "B render",
            "A componentWillUnmount",
            "B componentDidMount",
        ]
    finally:
        set_act_environment_enabled(False)


def test_should_cleanup_even_if_render_fatals() -> None:
    from ryact.hooks import _render_depth

    class BadComponent(Component):
        def render(self) -> object:
            raise RuntimeError("boom")

    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        with pytest.raises(RuntimeError, match="boom"), act(flush=root.flush):
            root.render(create_element(BadComponent))
        assert _render_depth == 0
    finally:
        set_act_environment_enabled(False)


@pytest.mark.skip(reason="Deferred: class cWM updating function child during mount needs noop harness ordering slice")
def test_should_not_warn_on_updating_function_component_from_componentwillmount() -> None:
    setter: list[Any] = []
    host_ref: list[Any] = []

    def A() -> object:
        v, set_v = use_state(None)
        setter.append(set_v)
        return create_element("div", {"ref": lambda n: host_ref.append(n), "children": str(v) if v is not None else ""})

    class B(Component):
        def UNSAFE_componentWillMount(self) -> None:  # noqa: N802
            setter[0](1)

        def render(self) -> object:
            return None

    def Parent() -> object:
        return create_element(
            "div",
            {"children": (create_element(A, {"key": "a"}), create_element(B, {"key": "b"}))},
        )

    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        with WarningCapture() as cap, act(flush=root.flush):
            root.render(create_element(Parent))
        assert not cap.records
        snap = root.get_children_snapshot()
        assert snap is not None and "1" in str(snap)
    finally:
        set_act_environment_enabled(False)


@pytest.mark.skip(reason="Deferred: class cWRP updating function child needs noop harness ordering slice")
def test_should_not_warn_on_updating_function_component_from_componentwillreceiveprops() -> None:
    setter: list[Any] = []
    host_ref: list[Any] = []

    def A() -> object:
        v, set_v = use_state(None)
        setter.append(set_v)
        return create_element("div", {"ref": lambda n: host_ref.append(n), "children": str(v) if v is not None else ""})

    class B(Component):
        def UNSAFE_componentWillReceiveProps(self, _np: object) -> None:  # noqa: N802
            setter[0](1)

        def render(self) -> object:
            return None

    def Parent() -> object:
        return create_element("div", {"children": (create_element(A), create_element(B, {"x": 0}))})

    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        with act(flush=root.flush):
            root.render(create_element(Parent))
        with WarningCapture() as cap, act(flush=root.flush):
            root.render(create_element(Parent, {"tick": 1}))
        assert not cap.records
        snap = root.get_children_snapshot()
        assert snap is not None and "1" in str(snap)
    finally:
        set_act_environment_enabled(False)


@pytest.mark.skip(reason="Deferred: class cWU updating function child needs noop harness ordering slice")
def test_should_not_warn_on_updating_function_component_from_componentwillupdate() -> None:
    setter: list[Any] = []
    host_ref: list[Any] = []

    def A() -> object:
        v, set_v = use_state(None)
        setter.append(set_v)
        return create_element("div", {"ref": lambda n: host_ref.append(n), "children": str(v) if v is not None else ""})

    class B(Component):
        def UNSAFE_componentWillUpdate(self, *_a: object) -> None:  # noqa: N802
            setter[0](1)

        def render(self) -> object:
            return None

    def Parent() -> object:
        return create_element("div", {"children": (create_element(A), create_element(B, {"x": 0}))})

    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        with act(flush=root.flush):
            root.render(create_element(Parent))
        with WarningCapture() as cap, act(flush=root.flush):
            root.render(create_element(Parent, {"tick": 1}))
        assert not cap.records
        snap = root.get_children_snapshot()
        assert snap is not None and "1" in str(snap)
    finally:
        set_act_environment_enabled(False)


def test_should_call_an_effect_after_mount_update_replacing_render_callback_pattern() -> None:
    log: list[str] = []

    def App() -> object:
        def eff() -> None:
            log.append("Callback")

        use_effect(eff)
        return create_element("div", {"children": "Foo"})

    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        with act(flush=root.flush):
            root.render(create_element(App))
        assert log == ["Callback"]
        log.clear()
        with act(flush=root.flush):
            root.render(create_element(App))
        assert log == ["Callback"]
    finally:
        set_act_environment_enabled(False)


def test_should_call_an_effect_when_the_same_element_is_re_rendered_replacing_render_callback_pattern() -> None:
    log: list[str] = []

    def App(*, prop: str) -> object:
        def eff() -> None:
            log.append("Callback")

        use_effect(eff)
        return create_element("div", {"children": prop})

    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        with act(flush=root.flush):
            root.render(create_element(App, {"prop": "Foo"}))
        assert log == ["Callback"]
        log.clear()
        with act(flush=root.flush):
            root.render(create_element(App, {"prop": "Bar"}))
        assert log == ["Callback"]
    finally:
        set_act_environment_enabled(False)


def test_should_render_one_portal() -> None:
    host = Container()
    portal_c = Container()
    root = create_root(host)
    set_act_environment_enabled(True)
    try:
        with act():
            root.render(
                create_element(
                    "div",
                    None,
                    create_portal(children=create_element("div", None, "portal"), container=portal_c),
                )
            )
        assert len(portal_c.root.children) == 1
        assert host.root.children and len(host.root.children) == 1
        with act():
            root.unmount()
        assert portal_c.root.children == []
        assert host.root.children == []
    finally:
        set_act_environment_enabled(False)
