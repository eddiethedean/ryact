# Translated from:
# - packages/react-dom/src/__tests__/ReactCompositeComponent-test.js
# - packages/react-dom/src/__tests__/ReactComponentLifeCycle-test.js
# Burndown v148: mount warnings, props/snapshot lifecycles, shallow SCU, CWRP batching.
from __future__ import annotations

import warnings
from typing import Any, cast

import pytest
from ryact import Component, create_element, create_ref
from ryact.component import _shallow_equal
from ryact.dev import is_dev, set_dev
from ryact_testkit import WarningCapture, act, create_noop_root, set_act_environment_enabled


def _snap_text(root: Any) -> str:
    snap = root.get_children_snapshot()
    if isinstance(snap, dict):
        return str(snap.get("props", {}).get("text", ""))
    return ""


def test_should_warn_about_setstate_on_not_yet_mounted_components() -> None:
    class MyComponent(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self.set_state({})

        def render(self) -> object:
            return create_element("span", {"text": "foo"})

    root = create_noop_root()
    with WarningCapture() as cap:
        root.render(create_element(MyComponent))
    assert any("Can't call setState on a component that is not yet mounted" in str(r.message) for r in cap.records)


def test_should_warn_about_forceupdate_on_not_yet_mounted_components() -> None:
    class MyComponent(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self.force_update()

        def render(self) -> object:
            return create_element("span", {"text": "foo"})

    root = create_noop_root()
    with WarningCapture() as cap:
        root.render(create_element(MyComponent))
    assert any("Can't call forceUpdate on a component that is not yet mounted" in str(r.message) for r in cap.records)


def test_should_not_warn_about_forceupdate_on_unmounted_components() -> None:
    box: dict[str, Any] = {}

    class App(Component):
        def componentDidMount(self) -> None:  # noqa: N802
            box["inst"] = self

        def render(self) -> object:
            return create_element("span")

    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        with act(flush=root.flush):
            root.render(create_element(App))
        inst = cast(Component, box["inst"])
        with act(flush=root.flush):
            root.render(None)
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            inst.force_update()
            inst.force_update()
    finally:
        set_act_environment_enabled(False)


def test_should_not_mutate_passed_in_props_object() -> None:
    class App(Component):
        defaultProps = {"prop": "testKey"}  # noqa: N815

        def render(self) -> object:
            return create_element("span", {"text": str(self.props.get("prop"))})

    input_props: dict[str, object] = {}
    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        with act(flush=root.flush):
            root.render(create_element(App, input_props))
        assert "prop" not in input_props
    finally:
        set_act_environment_enabled(False)


def test_should_warn_when_mutated_props_are_passed() -> None:
    class Foo(Component):
        def __init__(self, **props: object) -> None:
            mutated = {"idx": str(props.get("idx", "")) + "!"}
            super().__init__(**mutated)

        def render(self) -> object:
            return create_element("span", {"text": str(self.props.get("idx"))})

    root = create_noop_root()
    with WarningCapture() as cap:
        root.render(create_element(Foo, {"idx": "x"}))
    assert any("When calling super()" in str(r.message) and "same props" in str(r.message) for r in cap.records)


def test_should_disallow_nested_render_calls() -> None:
    class Inner(Component):
        def render(self) -> object:
            return create_element("span")

    class Outer(Component):
        def render(self) -> object:
            root.render(create_element(Inner))
            return create_element("div")

    root = create_noop_root()
    with WarningCapture() as cap:
        root.render(create_element(Outer))
    assert any("nested component updates from render is not allowed" in str(r.message) for r in cap.records)


def test_should_support_classes_shadowing_is_react_component() -> None:
    class Shadow(Component):
        def isReactComponent(self) -> None:  # noqa: N802
            pass

        def render(self) -> object:
            return create_element("div")

    root = create_noop_root()
    root.render(create_element(Shadow))
    root.flush()
    snap = root.get_children_snapshot()
    assert isinstance(snap, dict)
    assert snap.get("type") == "div"


def test_this_state_updated_on_setstate_callback_in_component_will_mount() -> None:
    flag = {"ok": False}

    class App(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self._state = {"hasUpdatedState": False}

        def UNSAFE_componentWillMount(self) -> None:  # noqa: N802
            self.set_state(
                {"hasUpdatedState": True},
                callback=lambda: flag.update(ok=bool(self.state["hasUpdatedState"])),
            )

        def render(self) -> object:
            return create_element("span", {"text": str(self.state["hasUpdatedState"])})

    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        with act(flush=root.flush):
            root.render(create_element(App))
        assert flag["ok"] is True
    finally:
        set_act_environment_enabled(False)


def test_does_not_do_deep_comparison_for_shallow_scu() -> None:
    log: list[str] = []

    def initial() -> dict[str, Any]:
        return {"foo": [1, 2, 3], "bar": {"a": 4, "b": 5, "c": 6}}

    settings = initial()

    class App(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self._state = dict(settings)

        def shouldComponentUpdate(self, np: object, ns: object) -> bool:  # noqa: N802
            return not _shallow_equal(self.props, np) or not _shallow_equal(self.state, ns)

        def render(self) -> object:
            foo = self.state["foo"]
            bar = self.state["bar"]
            log.append(f"foo:{foo},bar:{bar}")
            return create_element("span")

    root = create_noop_root()
    box: dict[str, Any] = {}

    class Tracked(App):
        def componentDidMount(self) -> None:  # noqa: N802
            box["inst"] = self

    set_act_environment_enabled(True)
    try:
        with act(flush=root.flush):
            root.render(create_element(Tracked))
        assert log == ["foo:[1, 2, 3],bar:{'a': 4, 'b': 5, 'c': 6}"]
        inst = cast(App, box["inst"])
        same = {"foo": settings["foo"], "bar": settings["bar"]}
        with act(flush=root.flush):
            inst.set_state(same)
        assert log == ["foo:[1, 2, 3],bar:{'a': 4, 'b': 5, 'c': 6}"]
        with act(flush=root.flush):
            inst.set_state({"foo": [1, 2, 3], "bar": settings["bar"]})
        assert len(log) == 2
        with act(flush=root.flush):
            inst.set_state(initial())
        assert len(log) == 3
    finally:
        set_act_environment_enabled(False)


def test_only_renders_once_if_updated_in_component_will_receive_props() -> None:
    renders = {"n": 0}
    box: dict[str, Any] = {}

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

    inst_ref = create_ref()
    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        with act(flush=root.flush):
            root.render(create_element(App, {"update": 0, "ref": inst_ref}))
        inst = cast(App, inst_ref.current)
        box["inst"] = inst
        assert renders["n"] == 1
        assert inst.state["updated"] is False
        with act(flush=root.flush):
            root.render(create_element(App, {"update": 1, "ref": inst_ref}))
        assert renders["n"] == 2
        assert box["inst"].state["updated"] is True
    finally:
        set_act_environment_enabled(False)


def test_should_warn_about_reassigning_this_props_while_rendering() -> None:
    class Bad(Component):
        def render(self) -> object:
            object.__setattr__(self, "_props", dict(self.props))
            return None

    root = create_noop_root()
    with WarningCapture() as cap:
        root.render(create_element(Bad))
    assert any("reassigning its own `this.props`" in str(r.message) for r in cap.records)


def test_should_not_support_module_pattern_components() -> None:
    def child(_props: object) -> dict[str, object]:
        return {"render": lambda: create_element("span")}

    root = create_noop_root()
    with pytest.raises((TypeError, ValueError)):
        root.render(create_element(child))


def test_should_allow_update_state_inside_component_will_mount() -> None:
    class App(Component):
        def UNSAFE_componentWillMount(self) -> None:  # noqa: N802
            self.set_state({"stateField": "something"})

        def render(self) -> object:
            return create_element("span", {"text": str(self.state.get("stateField"))})

    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        with act(flush=root.flush):
            root.render(create_element(App))
        assert _snap_text(root) == "something"
    finally:
        set_act_environment_enabled(False)


def test_warns_if_setting_this_state_equals_props() -> None:
    class App(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self._state = self._props

        def render(self) -> object:
            return create_element("div")

    root = create_noop_root()
    with WarningCapture() as cap:
        root.render(create_element(App, {"x": 1}))
    assert any("assign props directly to state" in str(r.message) for r in cap.records)


def test_should_warn_if_get_derived_state_from_props_returns_undefined() -> None:
    class App(Component):
        @staticmethod
        def getDerivedStateFromProps(_np: object, _st: object) -> object:  # noqa: N802
            return None

        def render(self) -> object:
            return None

    root = create_noop_root()
    with WarningCapture() as cap:
        root.render(create_element(App))
    assert any("getDerivedStateFromProps" in str(r.message) and "undefined" in str(r.message) for r in cap.records)


def test_should_pass_snapshot_from_get_snapshot_before_update_to_component_did_update() -> None:
    log: list[str] = []

    class App(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self._state = {"value": 0}

        @staticmethod
        def getDerivedStateFromProps(_np: object, prev_state: object) -> dict[str, int] | None:  # noqa: N802
            ps = cast(dict[str, Any], prev_state)
            return {"value": int(ps["value"]) + 1}

        def getSnapshotBeforeUpdate(self, prev_props: object, prev_state: object) -> str:  # noqa: N802
            pp = cast(dict[str, Any], prev_props)
            ps = cast(dict[str, Any], prev_state)
            log.append(f"gsbu:{pp['value']}:{ps['value']}")
            return "abc"

        def componentDidUpdate(self, prev_props: object, prev_state: object, snapshot: object) -> None:  # noqa: N802
            pp = cast(dict[str, Any], prev_props)
            ps = cast(dict[str, Any], prev_state)
            log.append(f"cdu:{pp['value']}:{ps['value']}:{snapshot}")

        def render(self) -> object:
            log.append("render")
            return None

    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        with act(flush=root.flush):
            root.render(create_element(App, {"value": "foo"}))
        assert log == ["render"]
        log.clear()
        with act(flush=root.flush):
            root.render(create_element(App, {"value": "bar"}))
        assert log == ["render", "gsbu:foo:1", "cdu:foo:1:abc"]
    finally:
        set_act_environment_enabled(False)


def test_should_pass_previous_state_to_scu_with_get_derived_state_from_props() -> None:
    class App(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self._state = {"value": 0}

        @staticmethod
        def getDerivedStateFromProps(np: object, prev_state: object) -> dict[str, Any] | None:  # noqa: N802
            nps = cast(dict[str, Any], np)
            pss = cast(dict[str, Any], prev_state)
            if nps["value"] == pss["value"]:
                return None
            return {"value": nps["value"]}

        def shouldComponentUpdate(self, _np: object, next_state: object) -> bool:  # noqa: N802
            nss = cast(dict[str, Any], next_state)
            return nss["value"] != self.state["value"]

        def render(self) -> object:
            return create_element("span", {"text": f"value: {self.state['value']}"})

    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        with act(flush=root.flush):
            root.render(create_element(App, {"value": "initial"}))
        assert _snap_text(root) == "value: initial"
        with act(flush=root.flush):
            root.render(create_element(App, {"value": "updated"}))
        assert _snap_text(root) == "value: updated"
    finally:
        set_act_environment_enabled(False)


def test_should_warn_if_get_snapshot_before_update_returns_undefined() -> None:
    class App(Component):
        def getSnapshotBeforeUpdate(self, _pp: object, _ps: object) -> None:  # noqa: N802
            return None

        def componentDidUpdate(self) -> None:  # noqa: N802
            pass

        def render(self) -> object:
            return None

    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        with act(flush=root.flush):
            root.render(create_element(App, {"value": "foo"}))
        with WarningCapture() as cap:
            with act(flush=root.flush):
                root.render(create_element(App, {"value": "bar"}))
        assert any("getSnapshotBeforeUpdate" in str(r.message) and "undefined" in str(r.message) for r in cap.records)
    finally:
        set_act_environment_enabled(False)


def test_should_warn_if_get_snapshot_before_update_without_component_did_update() -> None:
    class App(Component):
        def getSnapshotBeforeUpdate(self) -> None:  # noqa: N802
            return None

        def render(self) -> object:
            return None

    root = create_noop_root()
    with WarningCapture() as cap:
        root.render(create_element(App))
    assert any("getSnapshotBeforeUpdate() should be used with componentDidUpdate" in str(r.message) for r in cap.records)
