# Translated from:
# - packages/react-dom/src/__tests__/ReactCompositeComponent-test.js
# - packages/react-dom/src/__tests__/ReactComponentLifeCycle-test.js
# Burndown v147: class component composite + lifecycle (noop + DOM).
from __future__ import annotations

import warnings
from collections.abc import Iterator
from typing import Any, cast

import pytest
from ryact import Component, create_element, create_ref
from ryact.component import _shallow_equal
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


def test_should_call_setstate_callback_with_no_arguments() -> None:
    args_box: dict[str, tuple[Any, ...]] = {}

    class App(Component):
        def componentDidMount(self) -> None:  # noqa: N802
            self.set_state({}, callback=lambda *a: args_box.setdefault("args", a))

        def render(self) -> object:
            return create_element("span", {"text": "x"})

    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        with act(flush=root.flush):
            root.render(create_element(App))
        assert args_box.get("args") == ()
    finally:
        set_act_environment_enabled(False)


def test_should_call_setstate_callback_even_if_scu_false() -> None:
    log: list[str] = []

    class App(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self._state = {"n": 0}

        def shouldComponentUpdate(self, _np: object, _ns: object) -> bool:  # noqa: N802
            return False

        def componentDidMount(self) -> None:  # noqa: N802
            self.set_state({"n": 1}, callback=lambda: log.append("cb"))

        def render(self) -> object:
            return create_element("span", {"text": str(self.state["n"])})

    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        with act(flush=root.flush):
            root.render(create_element(App))
        assert log == ["cb"]
    finally:
        set_act_environment_enabled(False)


def test_respects_shallow_should_component_update() -> None:
    render_log: list[str] = []

    class Apple(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self._state = {"cut": False, "slices": 1}

        def shouldComponentUpdate(self, np: object, ns: object) -> bool:  # noqa: N802
            return not _shallow_equal(self.props, np) or not _shallow_equal(self.state, ns)

        def cut(self) -> None:
            self.set_state({"cut": True, "slices": 10})

        def render(self) -> object:
            render_log.append(f"{self.state['cut']},{self.state['slices']}")
            return create_element("span", {"text": "apple"})

    root = create_noop_root()
    box: dict[str, Any] = {}

    class AppleTracked(Apple):
        def componentDidMount(self) -> None:  # noqa: N802
            box["inst"] = self

    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        with act(flush=root.flush):
            root.render(create_element(AppleTracked))
        assert render_log == ["False,1"]
        inst = cast(Apple, box["inst"])
        with act(flush=root.flush):
            inst.cut()
        assert render_log == ["False,1", "True,10"]
        with act(flush=root.flush):
            inst.set_state({"slices": 9})
        assert render_log == ["False,1", "True,10", "True,9"]
        with act(flush=root.flush):
            inst.set_state({"slices": 9})
        assert render_log == ["False,1", "True,10", "True,9"]
    finally:
        set_act_environment_enabled(False)


def test_should_use_default_values_for_undefined_props() -> None:
    class App(Component):
        defaultProps = {"value": "default"}  # noqa: N815

        def render(self) -> object:
            return create_element("span", {"text": str(self.props.get("value"))})

    root = create_noop_root()
    root.render(create_element(App))
    root.flush()
    snap = root.get_children_snapshot()
    assert isinstance(snap, dict)
    assert snap.get("props", {}).get("text") == "default"


def test_should_skip_update_when_rerendering_element_in_container() -> None:
    log: list[str] = []

    class Child(Component):
        def render(self) -> object:
            log.append("Child")
            return create_element("span", {"text": "c"})

    class Parent(Component):
        def render(self) -> object:
            return self.props["children"]

    child_el = create_element(Child)
    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        with act(flush=root.flush):
            root.render(create_element(Parent, {"children": child_el}))
        assert log == ["Child"]
        with act(flush=root.flush):
            root.render(create_element(Parent, {"children": child_el}))
        assert log == ["Child"]
    finally:
        set_act_environment_enabled(False)


def test_should_silently_allow_setstate_not_call_cb_on_unmounting() -> None:
    cb_called = {"v": False}

    class App(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self._state = {"value": 0}

        def componentWillUnmount(self) -> None:  # noqa: N802
            self.set_state({"value": 2}, callback=lambda: cb_called.update(v=True))

        def render(self) -> object:
            return create_element("span", {"text": str(self.state["value"])})

    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        with act(flush=root.flush):
            root.render(create_element(App))
        with act(flush=root.flush):
            root.render(None)
        assert cb_called["v"] is False
    finally:
        set_act_environment_enabled(False)


def test_should_not_warn_about_setstate_on_unmounted_components() -> None:
    log: list[str] = []
    inst_ref = create_ref()

    class App(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self._state = {"value": 0}

        def render(self) -> object:
            log.append(f"render {self.state['value']}")
            return create_element("span", {"text": str(self.state["value"])})

    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        with act(flush=root.flush):
            root.render(create_element(App, {"ref": inst_ref}))
        assert log == ["render 0"]
        inst = cast(App, inst_ref.current)
        with act(flush=root.flush):
            inst.set_state({"value": 1})
        assert log == ["render 0", "render 1"]
        with act(flush=root.flush):
            root.render(None)
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            inst.set_state({"value": 2})
        assert log == ["render 0", "render 1"]
    finally:
        set_act_environment_enabled(False)


def test_should_warn_about_setstate_in_render() -> None:
    class App(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self._state = {"value": 0}

        def render(self) -> object:
            if self.state["value"] == 0:
                self.set_state({"value": 1})
            return create_element("span", {"text": str(self.state["value"])})

    root = create_noop_root()
    with WarningCapture() as cap:
        set_act_environment_enabled(True)
        try:
            with act(flush=root.flush):
                root.render(create_element(App))
        finally:
            set_act_environment_enabled(False)
    assert any("Cannot update during an existing state transition" in str(r.message) for r in cap.records)


def test_should_warn_when_component_did_receive_props_defined() -> None:
    class App(Component):
        def componentDidReceiveProps(self) -> None:  # noqa: N802
            pass

        def render(self) -> object:
            return create_element("span")

    root = create_noop_root()
    with WarningCapture() as cap:
        root.render(create_element(App))
    assert any("componentDidReceiveProps" in str(r.message) for r in cap.records)


def test_should_warn_when_component_did_unmount_defined() -> None:
    class App(Component):
        def componentDidUnmount(self) -> None:  # noqa: N802
            pass

        def render(self) -> object:
            return create_element("span")

    root = create_noop_root()
    with WarningCapture() as cap:
        root.render(create_element(App))
    assert any("componentDidUnmount" in str(r.message) for r in cap.records)


def test_should_warn_when_defaultprops_on_instance() -> None:
    class App(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self.defaultProps = {"x": 1}  # noqa: N815

        def render(self) -> object:
            return create_element("span")

    root = create_noop_root()
    with WarningCapture() as cap:
        root.render(create_element(App))
    assert any("defaultProps as an instance property" in str(r.message) for r in cap.records)


def test_should_warn_when_scu_returns_undefined() -> None:
    class App(Component):
        def shouldComponentUpdate(self, _np: object, _ns: object) -> object:  # noqa: N802
            return None

        def render(self) -> object:
            return create_element("span")

    root = create_noop_root()
    root.render(create_element(App))
    with WarningCapture() as cap:
        root.render(create_element(App))
    assert any("shouldComponentUpdate" in str(r.message) and "None" in str(r.message) for r in cap.records)


def test_should_allow_state_updates_in_component_did_mount() -> None:
    class App(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self._state = {"n": 0}

        def componentDidMount(self) -> None:  # noqa: N802
            self.set_state({"n": 1})

        def render(self) -> object:
            return create_element("span", {"text": str(self.state["n"])})

    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        with act(flush=root.flush):
            root.render(create_element(App))
        snap = root.get_children_snapshot()
        assert isinstance(snap, dict)
        assert snap.get("props", {}).get("text") == "1"
    finally:
        set_act_environment_enabled(False)


def test_should_not_render_extra_nodes_for_interpolated_text() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("div", None, "hello", 1, "world"))
    assert len(c.root.children) == 1
    div = c.root.children[0]
    assert len(div.children) == 3


def test_throws_if_render_not_defined() -> None:
    class MissingRender(Component):
        pass

    root = create_noop_root()
    with pytest.raises(TypeError, match="render"):
        root.render(create_element(MissingRender))
