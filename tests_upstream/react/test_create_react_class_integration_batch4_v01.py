from __future__ import annotations

from typing import Any

import pytest

from ryact import create_element
from ryact.create_react_class import create_react_class
from ryact.dev import set_dev
from ryact_testkit import WarningCapture, create_noop_root


def test_ismounted_works() -> None:
    ops: list[str] = []
    inst_holder: dict[str, Any] = {}

    def log(self: Any, name: str) -> None:
        ops.append(f"{name}: {self.isMounted()}")

    def render_fn(self: Any) -> Any:
        inst_holder.setdefault("i", self)
        self.log("render")
        return create_element("div", {"text": "x"})

    def unsafe_cwm(self: Any) -> None:
        self.log("mixin.componentWillMount")
        self.log("componentWillMount")

    def cdm(self: Any) -> None:
        self.log("mixin.componentDidMount")
        self.log("componentDidMount")

    def unsafe_cwu(self: Any) -> None:
        self.log("mixin.componentWillUpdate")
        self.log("componentWillUpdate")

    def cdu(self: Any) -> None:
        self.log("mixin.componentDidUpdate")
        self.log("componentDidUpdate")

    def cwu(self: Any) -> None:
        self.log("mixin.componentWillUnmount")
        self.log("componentWillUnmount")

    Component = create_react_class(
        {
            "displayName": "MyComponent",
            "log": log,
            "getInitialState": lambda self: (self.log("getInitialState"), {})[1],
            "UNSAFE_componentWillMount": unsafe_cwm,
            "componentDidMount": cdm,
            "UNSAFE_componentWillUpdate": unsafe_cwu,
            "componentDidUpdate": cdu,
            "componentWillUnmount": cwu,
            "render": render_fn,
        }
    )

    root = create_noop_root()
    with WarningCapture() as wc:
        root.render(create_element(Component))
        root.flush()
    wc.assert_any("isMounted is deprecated")

    root.render(create_element(Component))
    root.flush()

    inst = inst_holder["i"]
    root.render(None)
    root.flush()

    inst.log("after unmount")
    assert ops == [
        "getInitialState: False",
        "mixin.componentWillMount: False",
        "componentWillMount: False",
        "render: False",
        "mixin.componentDidMount: True",
        "componentDidMount: True",
        "mixin.componentWillUpdate: True",
        "componentWillUpdate: True",
        "render: True",
        "mixin.componentDidUpdate: True",
        "componentDidUpdate: True",
        "mixin.componentWillUnmount: True",
        "componentWillUnmount: True",
        "after unmount: False",
    ]


def test_renders_based_on_context_getinitialstate() -> None:
    Foo = create_react_class(
        {
            "contextTypes": {"className": object()},
            "getInitialState": lambda self: {"className": self.context.get("className", "")},
            "render": lambda self: create_element("div", {"className": self.state.get("className", "")}),
        }
    )
    Outer = create_react_class(
        {
            "childContextTypes": {"className": object()},
            "getChildContext": lambda self: {"className": "foo"},
            "render": lambda self: create_element(Foo),
        }
    )
    root = create_noop_root()
    root.render(create_element(Outer))
    root.flush()
    snap = root.get_children_snapshot()
    assert isinstance(snap, dict)
    assert snap.get("props", {}).get("className") == "foo"


def test_replace_state_and_callback_works() -> None:
    ops: list[str] = []
    inst_holder: dict[str, Any] = {}

    def render_fn(self: Any) -> Any:
        inst_holder["i"] = self
        ops.append(f"Render: {self.state.get('step')}")
        return create_element("div", {"text": str(self.state.get('step'))})

    Component = create_react_class(
        {
            "getInitialState": lambda self: {"step": 0},
            "render": render_fn,
        }
    )
    root = create_noop_root()
    root.render(create_element(Component))
    root.flush()
    inst = inst_holder["i"]
    inst.replace_state({"step": 1}, callback=lambda: ops.append(f"Callback: {inst.state.get('step')}"))
    root.flush()
    assert ops == ["Render: 0", "Render: 1", "Callback: 1"]


def test_should_invoke_both_deprecated_and_new_lifecycles_if_both_are_present() -> None:
    log: list[str] = []

    Component = create_react_class(
        {
            "displayName": "Component",
            "mixins": [
                {
                    "componentWillMount": lambda self: log.append("componentWillMount"),
                    "componentWillReceiveProps": lambda self, _np: log.append("componentWillReceiveProps"),
                    "componentWillUpdate": lambda self, _np: log.append("componentWillUpdate"),
                }
            ],
            "UNSAFE_componentWillMount": lambda self: log.append("UNSAFE_componentWillMount"),
            "UNSAFE_componentWillReceiveProps": lambda self, _np: log.append("UNSAFE_componentWillReceiveProps"),
            "UNSAFE_componentWillUpdate": lambda self: log.append("UNSAFE_componentWillUpdate"),
            "render": lambda self: create_element("div", {"text": "x"}),
        }
    )
    root = create_noop_root()
    with WarningCapture() as wc:
        root.render(create_element(Component))
        root.flush()
    wc.assert_any("componentWillMount has been renamed")
    assert log == ["componentWillMount", "UNSAFE_componentWillMount"]

    log.clear()
    with WarningCapture() as wc2:
        root.render(create_element(Component))
        root.flush()
    for phrase in ("componentWillReceiveProps has been renamed", "componentWillUpdate has been renamed"):
        wc2.assert_any(phrase)

    assert log == [
        "componentWillReceiveProps",
        "UNSAFE_componentWillReceiveProps",
        "componentWillUpdate",
        "UNSAFE_componentWillUpdate",
    ]


def test_should_not_invoke_deprecated_lifecycles_if_static_gdsfp_present() -> None:
    Component = create_react_class(
        {
            "displayName": "Component",
            "statics": {"getDerivedStateFromProps": lambda _np, _st: None},
            "componentWillMount": lambda self: (_ for _ in ()).throw(RuntimeError("unexpected")),
            "componentWillReceiveProps": lambda self, _np: (_ for _ in ()).throw(RuntimeError("unexpected")),
            "componentWillUpdate": lambda self, _np: (_ for _ in ()).throw(RuntimeError("unexpected")),
            "getInitialState": lambda self: {},
            "render": lambda self: create_element("div", {"text": "x"}),
        }
    )
    root = create_noop_root()
    with WarningCapture() as wc:
        root.render(create_element(Component))
        root.flush()
    wc.assert_any("Unsafe legacy lifecycles will not be called")
    wc.assert_any("getDerivedStateFromProps")
    for phrase in (
        "componentWillMount has been renamed",
        "componentWillReceiveProps has been renamed",
        "componentWillUpdate has been renamed",
    ):
        wc.assert_any(phrase)
    root.render(create_element(Component))
    root.flush()


def test_should_not_invoke_deprecated_lifecycles_if_get_snapshot_before_update_present() -> None:
    Component = create_react_class(
        {
            "displayName": "Component",
            "getSnapshotBeforeUpdate": lambda self: None,
            "componentWillMount": lambda self: (_ for _ in ()).throw(RuntimeError("unexpected")),
            "componentWillReceiveProps": lambda self, _np: (_ for _ in ()).throw(RuntimeError("unexpected")),
            "componentWillUpdate": lambda self, _np: (_ for _ in ()).throw(RuntimeError("unexpected")),
            "componentDidUpdate": lambda self: None,
            "render": lambda self: create_element("div", {"text": "x"}),
        }
    )
    root = create_noop_root()
    with WarningCapture() as wc:
        root.render(create_element(Component))
        root.flush()
    wc.assert_any("Unsafe legacy lifecycles will not be called")
    wc.assert_any("getSnapshotBeforeUpdate")
    root2 = create_noop_root()
    root2.render(create_element(Component))
    root2.flush()


def test_legacy_factory_call_throws() -> None:
    Component = create_react_class({"render": lambda self: create_element("div", {"text": "x"})})
    with WarningCapture() as wc, pytest.raises(TypeError):
        Component()
    wc.assert_any("React component directly")


def test_get_derived_state_from_props_post_assign_return_values() -> None:
    Component = create_react_class(
        {
            "getInitialState": lambda self: {},
            "render": lambda self: create_element("div", {"text": self.state.get("occupation", "")}),
        }
    )

    def _gdsfp(_np: dict[str, Any], _st: dict[str, Any]) -> dict[str, str]:
        return {"occupation": "clown"}

    Component.getDerivedStateFromProps = staticmethod(_gdsfp)  # type: ignore[method-assign]

    root = create_noop_root()
    root.render(create_element(Component))
    root.flush()
    assert root.get_children_snapshot()["props"]["text"] == "clown"


def test_warns_if_get_derived_state_from_error_is_not_static() -> None:
    set_dev(True)
    Bomb = create_react_class(
        {
            "render": lambda self: (_ for _ in ()).throw(RuntimeError("boom")),
        }
    )

    def render_b(self: Any) -> Any:
        if self.state.get("error"):
            return create_element("div", {"text": "fallback"})
        ch = self.props.get("children")
        if ch is None:
            return create_element("div", {"text": "empty"})
        return create_element("div", None, ch)

    Boundary = create_react_class(
        {
            "displayName": "Foo",
            "getInitialState": lambda self: {"error": False},
            "componentDidCatch": lambda self, _err: self._state.update({"error": True}),  # type: ignore[attr-defined]
            "render": render_b,
        }
    )

    def bad(self: Any, _err: BaseException) -> dict[str, Any]:
        return {}

    Boundary.getDerivedStateFromError = bad  # type: ignore[method-assign]

    root = create_noop_root()
    with WarningCapture() as wc:
        root.render(create_element(Boundary, {"children": create_element(Bomb)}))
        root.flush()
    wc.assert_any("getDerivedStateFromError")
    wc.assert_any("staticmethod")


def test_warns_if_get_derived_state_from_props_is_not_static() -> None:
    Foo = create_react_class(
        {
            "displayName": "Foo",
            "render": lambda self: create_element("div", {"text": "x"}),
        }
    )

    def _bad(self: Any, _np: dict[str, Any], _st: dict[str, Any]) -> dict[str, Any]:
        return {}

    Foo.getDerivedStateFromProps = _bad  # type: ignore[method-assign]

    root = create_noop_root()
    with WarningCapture() as wc:
        root.render(create_element(Foo))
        root.flush()
    wc.assert_any("getDerivedStateFromProps")
    wc.assert_any("staticmethod")
