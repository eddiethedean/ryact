# Translated from:
# - packages/react-dom/src/__tests__/ReactCompositeComponent-test.js
# - packages/react-dom/src/__tests__/ReactComponentLifeCycle-test.js
# - packages/react-dom/src/__tests__/ReactDOMFiber-test.js
# - packages/react-dom/src/__tests__/ReactComponent-test.js
# Burndown v149: CWRP batching, cWU ordering, gDSFP/gSBU legacy suppression, host children.
from __future__ import annotations

from collections.abc import Iterator
from typing import Any, cast

import pytest
from ryact import Component, create_element, create_ref
from ryact.concurrent import Fragment
from ryact.dev import is_dev, set_dev
from ryact_dom.dom import Container
from ryact_dom.root import create_root
from ryact_testkit import WarningCapture, act, create_noop_root, set_act_environment_enabled


@pytest.fixture(autouse=True)
def _dev_on() -> Iterator[None]:
    prev = is_dev()
    set_dev(True)
    yield
    set_dev(prev)


def test_only_renders_once_if_updated_in_cwrp_when_batching() -> None:
    renders = {"n": 0}
    inst_ref = create_ref()

    class App(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self._state = {"updated": False}

        def componentWillReceiveProps(self, props: object) -> None:  # noqa: N802
            assert cast(dict[str, Any], props)["update"] == 1
            assert renders["n"] == 1
            self.set_state({"updated": True})
            assert renders["n"] == 1

        def render(self) -> object:
            renders["n"] += 1
            return create_element("span")

    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        with act(flush=root.flush):
            root.render(create_element(App, {"update": 0, "ref": inst_ref}))
        inst = cast(App, inst_ref.current)
        assert renders["n"] == 1
        assert inst.state["updated"] is False
        with act(flush=root.flush):
            root.batched_updates(lambda: root.render(create_element(App, {"update": 1, "ref": inst_ref})))
        assert renders["n"] == 2
        assert inst.state["updated"] is True
    finally:
        set_act_environment_enabled(False)


def test_should_only_call_component_will_unmount_once() -> None:
    count = {"n": 0}
    app_ref = create_ref()

    class App(Component):
        def render(self) -> object:
            if self.props.get("stage") == 1:
                return create_element(Unmountable, {"name": "x"})
            return None

    class Unmountable(Component):
        def componentWillUnmount(self) -> None:  # noqa: N802
            cast(App, app_ref.current).set_state({})
            count["n"] += 1
            raise RuntimeError("always fails")

        def render(self) -> object:
            return create_element("span", {"text": self.props.get("name", "")})

    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        with act(flush=root.flush):
            root.render(create_element(App, {"stage": 1, "ref": app_ref}))
        with act(flush=root.flush):
            root.render(create_element(App, {"stage": 2, "ref": app_ref}))
        assert count["n"] == 1
    finally:
        set_act_environment_enabled(False)


def test_should_call_component_will_unmount_before_unmounting() -> None:
    inner_unmounted = {"v": False}

    class Inner(Component):
        def componentWillUnmount(self) -> None:  # noqa: N802
            inner_unmounted["v"] = True

        def render(self) -> object:
            return create_element("span", {"text": "inner"})

    class Outer(Component):
        def render(self) -> object:
            return create_element("div", None, create_element(Inner))

    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        with act(flush=root.flush):
            root.render(create_element(Outer))
        with act(flush=root.flush):
            root.render(None)
        assert inner_unmounted["v"] is True
    finally:
        set_act_environment_enabled(False)


def test_should_warn_class_render_not_extending_component() -> None:
    class ClassWithRenderNotExtended:
        def render(self) -> object:
            return create_element("div")

    root = create_noop_root()
    with WarningCapture() as cap:
        with pytest.raises(TypeError, match="doesn't extend"):
            root.render(create_element(ClassWithRenderNotExtended))
    assert any("doesn't extend" in str(r.message) for r in cap.records)


def test_should_not_invoke_deprecated_lifecycles_with_gdsfp() -> None:
    class App(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self._state = {}

        @staticmethod
        def getDerivedStateFromProps(_np: object, _st: object) -> None:  # noqa: N802
            return None

        def componentWillMount(self) -> None:  # noqa: N802
            raise RuntimeError("unexpected cWM")

        def componentWillReceiveProps(self) -> None:  # noqa: N802
            raise RuntimeError("unexpected cWRP")

        def componentWillUpdate(self) -> None:  # noqa: N802
            raise RuntimeError("unexpected cWU")

        def render(self) -> object:
            return None

    root = create_noop_root()
    with WarningCapture() as cap:
        root.render(create_element(App))
    assert any("Unsafe legacy lifecycles will not be called" in str(r.message) for r in cap.records)


def test_should_not_invoke_deprecated_lifecycles_with_gsbu() -> None:
    class App(Component):
        def getSnapshotBeforeUpdate(self, _pp: object, _ps: object) -> None:  # noqa: N802
            return None

        def componentDidUpdate(self) -> None:  # noqa: N802
            pass

        def componentWillMount(self) -> None:  # noqa: N802
            raise RuntimeError("unexpected cWM")

        def render(self) -> object:
            return None

    root = create_noop_root()
    root.render(create_element(App))


def test_should_invoke_both_deprecated_and_new_lifecycles() -> None:
    log: list[str] = []

    class App(Component):
        def componentWillMount(self) -> None:  # noqa: N802
            log.append("componentWillMount")

        def UNSAFE_componentWillMount(self) -> None:  # noqa: N802
            log.append("UNSAFE_componentWillMount")

        def componentWillReceiveProps(self, _props: object) -> None:  # noqa: N802
            log.append("componentWillReceiveProps")

        def UNSAFE_componentWillReceiveProps(self, _props: object) -> None:  # noqa: N802
            log.append("UNSAFE_componentWillReceiveProps")

        def componentWillUpdate(self, _np: object, _ns: object) -> None:  # noqa: N802
            log.append("componentWillUpdate")

        def UNSAFE_componentWillUpdate(self, _np: object, _ns: object) -> None:  # noqa: N802
            log.append("UNSAFE_componentWillUpdate")

        def render(self) -> object:
            return None

    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        with act(flush=root.flush):
            root.render(create_element(App, {"x": 1}))
        assert log == ["componentWillMount", "UNSAFE_componentWillMount"]
        log.clear()
        with act(flush=root.flush):
            root.render(create_element(App, {"x": 2}))
        assert log == [
            "componentWillReceiveProps",
            "UNSAFE_componentWillReceiveProps",
            "componentWillUpdate",
            "UNSAFE_componentWillUpdate",
        ]
    finally:
        set_act_environment_enabled(False)


def test_should_not_allow_setstate_in_constructor() -> None:
    class App(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self.set_state({"stateField": "something"})
            self._state = {"stateField": "somethingelse"}

        def render(self) -> object:
            return create_element("div")

    root = create_noop_root()
    with WarningCapture() as cap:
        root.render(create_element(App))
    assert any("Can't call setState on a component that is not yet mounted" in str(r.message) for r in cap.records)


def test_renders_empty_fragment() -> None:
    c = Container()
    r = create_root(c)

    def empty_fragment() -> object:
        return create_element(Fragment)

    def with_div() -> object:
        return create_element(Fragment, None, create_element("div"))

    r.render(create_element(empty_fragment))
    assert len(c.root.children) == 0
    r.render(create_element(with_div))
    assert len(c.root.children) == 1
    r.render(create_element(empty_fragment))
    assert len(c.root.children) == 0


def test_should_render_strings_as_children() -> None:
    c = Container()
    r = create_root(c)

    def box(**props: object) -> object:
        return create_element("span", None, props["value"])

    r.render(create_element(box, {"value": "foo"}))
    assert c.text_content == "foo"


def test_should_render_numbers_as_children() -> None:
    c = Container()
    r = create_root(c)

    def box(**props: object) -> object:
        return create_element("span", None, props["value"])

    r.render(create_element(box, {"value": 10}))
    assert c.text_content == "10"


def test_should_render_bigints_as_children() -> None:
    c = Container()
    r = create_root(c)

    def box(**props: object) -> object:
        return create_element("span", None, props["value"])

    r.render(create_element(box, {"value": 10}))
    assert c.text_content == "10"


def test_throws_plain_object_as_child() -> None:
    children = {"x": 1, "y": 2, "z": 3}

    class App(Component):
        def render(self) -> object:
            return create_element("div", None, children)

    root = create_noop_root()
    with pytest.raises(TypeError, match="Objects are not valid as a React child"):
        root.render(create_element(App))


def test_throws_plain_object_in_owner() -> None:
    class App(Component):
        def render(self) -> object:
            return create_element("div", None, {"a": 1, "b": 2, "c": 3})

    root = create_noop_root()
    with pytest.raises(TypeError, match="Objects are not valid as a React child"):
        root.render(create_element(App))


def test_warns_function_as_child_to_host() -> None:
    def foo() -> str:
        return "x"

    class App(Component):
        def render(self) -> object:
            return create_element("div", None, create_element("span", None, foo))

    root = create_noop_root()
    with WarningCapture() as cap:
        root.render(create_element(App))
    assert any("Functions are not valid as a React child" in str(r.message) for r in cap.records)


def test_should_render_component_returning_numbers_directly() -> None:
    class App(Component):
        def render(self) -> object:
            return 10

    root = create_noop_root()
    root.render(create_element(App))
    snap = root.get_children_snapshot()
    assert snap == "10" or snap == 10
