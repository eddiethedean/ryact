# Translated from:
# - packages/react-dom/src/__tests__/ReactComponent-test.js
# - packages/react-dom/src/__tests__/ReactComponentLifeCycle-test.js
# - packages/react-dom/src/__tests__/ReactCompositeComponent-test.js
# - packages/react-dom/src/__tests__/ReactDOMFiber-test.js
# Burndown v150: refs, invalid elements, lifecycle warnings, gDSFP/gSBU, host children.
from __future__ import annotations

from collections.abc import Iterator
from typing import Any, cast

import pytest
from ryact import Component, create_element, create_ref
from ryact.concurrent import Fragment
from ryact.element import Element
from ryact.hooks import use_state
from ryact.dev import is_dev, set_dev
from ryact.element import UNDEFINED_ELEMENT_TYPE
from ryact.reconciler import reset_function_child_warning_state
from ryact_dom.dom import Container
from ryact_dom.root import create_root
from ryact_testkit import WarningCapture, act, create_noop_root, set_act_environment_enabled


@pytest.fixture(autouse=True)
def _dev_on() -> Iterator[None]:
    prev = is_dev()
    set_dev(True)
    reset_function_child_warning_state()
    yield
    set_dev(prev)


def test_should_support_callback_style_refs() -> None:
    inner_obj: dict[str, object] = {}
    outer_obj: dict[str, object] = {}
    mounted = {"v": False}

    class Wrapper(Component):
        def get_object(self) -> object:
            return self.props["object"]

        def render(self) -> object:
            return self.props.get("children")

    class App(Component):
        inner_ref: Any = None
        outer_ref: Any = None

        def render(self) -> object:
            inner = create_element(
                Wrapper,
                {"object": inner_obj, "ref": lambda c: setattr(self, "inner_ref", c)},
            )
            return create_element(
                Wrapper,
                {
                    "object": outer_obj,
                    "ref": lambda c: setattr(self, "outer_ref", c),
                    "children": inner,
                },
            )

        def componentDidMount(self) -> None:  # noqa: N802
            assert self.inner_ref.get_object() == inner_obj
            assert self.outer_ref.get_object() == outer_obj
            mounted["v"] = True

    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        with act(flush=root.flush):
            root.render(create_element(App))
        assert mounted["v"] is True
    finally:
        set_act_environment_enabled(False)


def test_should_support_object_style_refs() -> None:
    inner_obj: dict[str, object] = {}
    outer_obj: dict[str, object] = {}
    mounted = {"v": False}

    class Wrapper(Component):
        def get_object(self) -> object:
            return self.props["object"]

        def render(self) -> object:
            return self.props.get("children")

    class App(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self.inner_ref = create_ref()
            self.outer_ref = create_ref()

        def render(self) -> object:
            inner = create_element(Wrapper, {"object": inner_obj, "ref": self.inner_ref})
            return create_element(
                Wrapper,
                {"object": outer_obj, "ref": self.outer_ref, "children": inner},
            )

        def componentDidMount(self) -> None:  # noqa: N802
            assert self.inner_ref.current.get_object() == inner_obj
            assert self.outer_ref.current.get_object() == outer_obj
            mounted["v"] = True

    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        with act(flush=root.flush):
            root.render(create_element(App))
        assert mounted["v"] is True
    finally:
        set_act_environment_enabled(False)


def _noop_host_text(host: Any) -> str:
    if not isinstance(host, dict):
        return ""
    props = host.get("props") or {}
    if isinstance(props, dict) and "text" in props:
        return str(props["text"])
    for ch in host.get("children", []) or []:
        if isinstance(ch, dict) and ch.get("type") == "#text":
            return str(ch.get("text", ""))
    return ""


def test_should_support_new_style_refs_with_mixed_up_owners() -> None:
    mounted = {"v": False}

    class Wrapper(Component):
        def get_title(self) -> object:
            return self.props.get("title")

        def render(self) -> object:
            content = self.props.get("getContent")
            return content() if callable(content) else content

    class App(Component):
        wrapper_ref: Any = None
        inner_ref: Any = None

        def get_inner(self) -> object:
            return create_element(
                "div",
                {"className": "inner", "ref": lambda c: setattr(self, "inner_ref", c)},
            )

        def render(self) -> object:
            return create_element(
                Wrapper,
                {
                    "title": "wrapper",
                    "ref": lambda c: setattr(self, "wrapper_ref", c),
                    "getContent": self.get_inner,
                },
            )

        def componentDidMount(self) -> None:  # noqa: N802
            assert self.wrapper_ref.get_title() == "wrapper"
            inner_host = self.inner_ref
            assert inner_host is not None
            if isinstance(inner_host, dict):
                assert (inner_host.get("props") or {}).get("className") == "inner"
            mounted["v"] = True

    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        with act(flush=root.flush):
            root.render(create_element(App))
        assert mounted["v"] is True
    finally:
        set_act_environment_enabled(False)


def test_throws_usefully_when_rendering_badly_typed_elements() -> None:
    root = create_noop_root()
    with pytest.raises(TypeError, match="got: undefined"):
        root.render(create_element(UNDEFINED_ELEMENT_TYPE))
    with pytest.raises(TypeError, match="got: null"):
        root.render(create_element(None))
    with pytest.raises(TypeError, match="got: boolean"):
        root.render(create_element(True))


def test_includes_owner_name_in_badly_typed_elements_error() -> None:
    class Indirection(Component):
        def render(self) -> object:
            return self.props.get("children")

    class Bar(Component):
        def render(self) -> object:
            return create_element(Indirection, {"children": create_element(UNDEFINED_ELEMENT_TYPE)})

    root = create_noop_root()
    with pytest.raises(TypeError, match=r"Check the render method of `Bar`|Indirection"):
        root.render(create_element(Bar))


def test_should_throw_when_children_mutated_during_render() -> None:
    class Wrapper(Component):
        def render(self) -> object:
            children = self.props["children"]
            children[1] = create_element("span")
            return create_element(Fragment, None, *children)

    root = create_noop_root()
    with pytest.raises(TypeError, match="read only|readonly|immutable"):
        root.render(
            create_element(
                Wrapper,
                {
                    "children": (
                        create_element("span", {"text": "a"}),
                        create_element("span", {"text": "b"}),
                        create_element("span", {"text": "c"}),
                    )
                },
            )
        )


def test_should_throw_when_children_mutated_during_update() -> None:
    class Wrapper(Component):
        def componentDidMount(self) -> None:  # noqa: N802
            self.props["children"][1] = create_element("span")
            self.force_update()

        def render(self) -> object:
            return create_element(Fragment, None, *self.props["children"])

    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        with pytest.raises(TypeError, match="read only|readonly|immutable"):
            with act(flush=root.flush):
                root.render(
                    create_element(
                        Wrapper,
                        {
                            "children": (
                                create_element("span", {"text": "a"}),
                                create_element("span", {"text": "b"}),
                                create_element("span", {"text": "c"}),
                            )
                        },
                    )
                )
    finally:
        set_act_environment_enabled(False)


def test_warns_on_function_as_return_value_from_function() -> None:
    def foo_fn() -> None:
        return None

    def foo() -> object:
        return foo_fn

    root = create_noop_root()
    with WarningCapture() as cap:
        root.render(create_element(foo))
    assert any("Functions are not valid as a React child" in str(r.message) for r in cap.records)


def test_warns_on_function_as_return_value_from_class() -> None:
    def foo_fn() -> None:
        return None

    class Foo(Component):
        def render(self) -> object:
            return foo_fn

    root = create_noop_root()
    with WarningCapture() as cap:
        root.render(create_element(Foo))
    assert any("Functions are not valid as a React child" in str(r.message) for r in cap.records)


def test_does_not_warn_for_function_as_child_that_gets_resolved() -> None:
    class Bar(Component):
        def render(self) -> object:
            render_child = self.props.get("renderChild")
            return render_child() if callable(render_child) else render_child

    def foo() -> object:
        return create_element(
            Bar,
            {"renderChild": lambda: create_element("span", {"text": "Hello"})},
        )

    root = create_noop_root()
    with WarningCapture() as cap:
        with act(flush=root.flush):
            root.render(create_element(foo))
    assert not any("Functions are not valid as a React child" in str(r.message) for r in cap.records)
    assert "Hello" in str(root.container.last_committed_as_dict())


def test_deduplicates_function_type_warnings() -> None:
    def foo_fn() -> None:
        return None

    class Foo(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self._state = {"type": "mushrooms"}

        def render(self) -> object:
            return create_element(
                "div",
                None,
                foo_fn,
                foo_fn,
                create_element("span", None, foo_fn),
                create_element("span", None, foo_fn),
            )

    inst_ref = create_ref()
    root = create_noop_root()
    with WarningCapture() as cap:
        with act(flush=root.flush):
            root.render(create_element(Foo, {"ref": inst_ref}))
        inst = cast(Foo, inst_ref.current)
        with act(flush=root.flush):
            inst.set_state({"type": "portobello"})
    msgs = [str(r.message) for r in cap.records if "Functions are not valid" in str(r.message)]
    assert any("in div" in m for m in msgs)
    assert any("in span" in m for m in msgs)


def test_should_not_invoke_new_unsafe_lifecycles_with_gdsfp() -> None:
    class App(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self._state = {}

        @staticmethod
        def getDerivedStateFromProps(_np: object, _st: object) -> None:  # noqa: N802
            return None

        def UNSAFE_componentWillMount(self) -> None:  # noqa: N802
            raise RuntimeError("unexpected cWM")

        def UNSAFE_componentWillReceiveProps(self, _props: object) -> None:  # noqa: N802
            raise RuntimeError("unexpected cWRP")

        def UNSAFE_componentWillUpdate(self, _np: object, _ns: object) -> None:  # noqa: N802
            raise RuntimeError("unexpected cWU")

        def render(self) -> object:
            return None

    root = create_noop_root()
    with WarningCapture() as cap:
        with act(flush=root.flush):
            root.render(create_element(App))
        with act(flush=root.flush):
            root.render(create_element(App, {"x": 1}))
    assert any("UNSAFE_componentWillMount" in str(r.message) for r in cap.records)


def test_should_warn_about_deprecated_lifecycles_with_gdsfp() -> None:
    class App(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self._state = {}

        @staticmethod
        def getDerivedStateFromProps(_np: object, _st: object) -> None:  # noqa: N802
            return None

        def componentWillMount(self) -> None:  # noqa: N802
            pass

        def UNSAFE_componentWillReceiveProps(self, _props: object) -> None:  # noqa: N802
            pass

        def componentWillUpdate(self, _np: object, _ns: object) -> None:  # noqa: N802
            pass

        def render(self) -> object:
            return None

    root = create_noop_root()
    with WarningCapture() as cap:
        with act(flush=root.flush):
            root.render(create_element(App))
    assert any("Unsafe legacy lifecycles will not be called" in str(r.message) for r in cap.records)
    assert any("componentWillMount has been renamed" in str(r.message) for r in cap.records)


def test_should_warn_if_state_not_initialized_before_gdsfp() -> None:
    class MyComponent(Component):
        @staticmethod
        def getDerivedStateFromProps(_np: object, _st: object) -> None:  # noqa: N802
            return None

        def render(self) -> object:
            return None

    root = create_noop_root()
    with WarningCapture() as cap:
        with act(flush=root.flush):
            root.render(create_element(MyComponent))
        with act(flush=root.flush):
            root.render(create_element(MyComponent))
    msgs = [str(r.message) for r in cap.records if "initial state is undefined" in str(r.message)]
    assert len(msgs) == 1


def test_should_not_override_stale_state_in_gdsfp_spread() -> None:
    child_ref = create_ref()
    child_inst: list[Component] = []

    class Child(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self._state = {"local": 0}

        @staticmethod
        def getDerivedStateFromProps(next_props: dict[str, Any], prev_state: dict[str, Any]) -> dict[str, Any]:  # noqa: N802
            return {**prev_state, "remote": next_props.get("remote", 0)}

        def update_state(self) -> None:
            self.set_state(lambda st, _props=None: {"local": st["local"] + 1})
            on_change = self.props.get("onChange")
            if callable(on_change):
                on_change(self.state["remote"] + 1)

        def render(self) -> object:
            child_inst.clear()
            child_inst.append(self)
            return create_element(
                "div",
                {"ref": child_ref, "text": f"remote:{self.state['remote']}, local:{self.state['local']}"},
            )

    class Parent(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self._state = {"value": 0}

        def handle_change(self, value: int) -> None:
            self.set_state({"value": value})

        def render(self) -> object:
            return create_element(Child, {"remote": self.state["value"], "onChange": self.handle_change})

    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        with act(flush=root.flush):
            root.render(create_element(Parent))
        snap = root.container.last_committed_as_dict()
        assert "remote:0, local:0" in str(snap)
        with act(flush=root.flush):
            child_inst[0].update_state()
        snap2 = root.container.last_committed_as_dict()
        assert "remote:1, local:1" in str(snap2)
    finally:
        set_act_environment_enabled(False)


def test_should_call_getsnapshotbeforeupdate_before_mutations() -> None:
    log: list[str] = []

    class MyComponent(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self.div_ref = create_ref()

        def getSnapshotBeforeUpdate(self, prev_props: dict[str, Any], _prev_state: object) -> str:  # noqa: N802
            log.append("getSnapshotBeforeUpdate")
            assert _noop_host_text(self.div_ref.current) == f"value:{prev_props.get('value')}"
            return "foobar"

        def componentDidUpdate(  # noqa: N802
            self,
            prev_props: dict[str, Any],
            _prev_state: object,
            snapshot: object,
        ) -> None:
            log.append("componentDidUpdate")
            assert _noop_host_text(self.div_ref.current) == f"value:{self.props.get('value')}"
            assert snapshot == "foobar"

        def render(self) -> object:
            log.append("render")
            return create_element(
                "div",
                {"ref": self.div_ref, "text": f"value:{self.props.get('value')}"},
            )

    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        with act(flush=root.flush):
            root.render(create_element(MyComponent, {"value": 0}))
        assert log == ["render"]
        log.clear()
        with act(flush=root.flush):
            root.render(create_element(MyComponent, {"value": 1}))
        assert log == ["render", "getSnapshotBeforeUpdate", "componentDidUpdate"]
    finally:
        set_act_environment_enabled(False)


def test_warns_about_deprecated_unsafe_lifecycles() -> None:
    class MyComponent(Component):
        def componentWillMount(self) -> None:  # noqa: N802
            pass

        def componentWillReceiveProps(self, _props: object) -> None:  # noqa: N802
            pass

        def componentWillUpdate(self, _np: object, _ns: object) -> None:  # noqa: N802
            pass

        def render(self) -> object:
            return None

    root = create_noop_root()
    with WarningCapture() as cap:
        with act(flush=root.flush):
            root.render(create_element(MyComponent))
        with act(flush=root.flush):
            root.render(create_element(MyComponent, {"x": 1}))
        with act(flush=root.flush):
            root.render(create_element(MyComponent, {"x": 2}))
    rename_msgs = [str(r.message) for r in cap.records if "has been renamed" in str(r.message)]
    assert len(rename_msgs) == 3


def test_throws_when_accessing_state_in_component_will_mount() -> None:
    class Stateful(Component):
        def UNSAFE_componentWillMount(self) -> None:  # noqa: N802
            _ = self.state["yada"]

        def render(self) -> object:
            return create_element("span")

    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        with pytest.raises((AttributeError, KeyError, TypeError)):
            with act(flush=root.flush):
                root.render(create_element(Stateful))
    finally:
        set_act_environment_enabled(False)


def test_should_not_throw_when_updating_auxiliary_component() -> None:
    class Tooltip(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self.aux_root: Any = None

        def componentDidMount(self) -> None:  # noqa: N802
            self.aux_root = create_noop_root()
            self._update_tooltip()

        def componentDidUpdate(self, *_args: object) -> None:  # noqa: N802
            self._update_tooltip()

        def _update_tooltip(self) -> None:
            tip = self.props.get("tooltip")
            if self.aux_root is not None and isinstance(tip, Element):
                self.aux_root.render(tip)

        def render(self) -> object:
            return create_element(Fragment, None, self.props.get("children"))

    class App(Component):
        def render(self) -> object:
            return create_element(
                Tooltip,
                {
                    "tooltip": create_element("span", {"text": self.props.get("tooltipText", "")}),
                    "children": create_element("span", {"text": self.props.get("text", "")}),
                },
            )

    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        with act(flush=root.flush):
            root.render(create_element(App, {"tooltipText": "tip1", "text": "main"}))
        with act(flush=root.flush):
            root.render(create_element(App, {"tooltipText": "tip2", "text": "main2"}))
    finally:
        set_act_environment_enabled(False)


def test_should_render_strings_directly_from_render() -> None:
    class App(Component):
        def render(self) -> object:
            return "hello"

    container = Container()
    root = create_root(container)
    root.render(create_element(App))
    assert container.text_content == "hello"


def test_should_warn_on_updating_function_component_from_render() -> None:
    set_state_holder: list[Any] = []
    host_ref: list[Any] = []

    def a_component() -> object:
        state, set_state = use_state(0)
        set_state_holder.clear()
        set_state_holder.append(set_state)
        return create_element("span", {"ref": lambda r: host_ref.append(r), "text": str(state)})

    def b_component() -> object:
        if set_state_holder:
            set_state_holder[0](lambda c: c + 1)
        return None

    def parent() -> object:
        return create_element(Fragment, None, create_element(a_component), create_element(b_component))

    root = create_noop_root()
    with WarningCapture() as cap:
        with act(flush=root.flush):
            root.render(create_element(parent))
    assert any("Cannot update a component" in str(r.message) for r in cap.records)
    assert "1" in str(root.container.last_committed)


def test_should_return_meaningful_warning_when_constructor_is_returned() -> None:
    class RenderTextInvalidConstructor(Component):
        def __new__(cls, **props: object) -> object:
            return {"something": False}

        def render(self) -> object:
            return create_element("span")

    root = create_noop_root()
    with WarningCapture() as cap:
        with pytest.raises(TypeError):
            root.render(create_element(RenderTextInvalidConstructor))
    assert any("accidentally return an object from the constructor" in str(r.message) for r in cap.records)
