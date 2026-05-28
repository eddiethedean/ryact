# Translated from: packages/react-dom/src/__tests__/ReactUpdates-test.js
# Burndown v146: deferred SCU bailout, props-child reuse, CWRP callbacks, reentrant commit.
from __future__ import annotations

from typing import Any, cast

from ryact import Children, Component, create_element, create_ref
from ryact_testkit import act, create_noop_root, set_act_environment_enabled


def test_should_batch_forceupdate_together() -> None:
    log: list[str] = []
    box: dict[str, Any] = {}
    should_update_count = {"n": 0}

    class Comp(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self._state = {"x": 0}
            box["inst"] = self

        def shouldComponentUpdate(self, _np: object, _ns: object) -> bool:  # noqa: N802
            should_update_count["n"] += 1
            return True

        def componentDidUpdate(self, *_args: object) -> None:  # noqa: N802
            log.append("Update")

        def render(self) -> object:
            return create_element("span", {"text": str(self.state["x"])})

    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        with act(flush=root.flush):
            root.render(create_element(Comp))
        assert log == []
        assert box["inst"].state["x"] == 0

        with act(flush=root.flush):
            box["inst"].set_state({"x": 1}, callback=lambda: log.append("callback"))
            box["inst"].force_update(callback=lambda: log.append("forceUpdate"))
            assert log == []
            assert box["inst"].state["x"] == 0
            assert _snap_text(root) == "0"

        assert should_update_count["n"] == 0
        assert log == ["Update", "callback", "forceUpdate"]
        assert box["inst"].state["x"] == 1
        assert _snap_text(root) == "1"
    finally:
        set_act_environment_enabled(False)


def test_should_update_children_even_if_parent_blocks_updates() -> None:
    log: list[str] = []
    box: dict[str, Any] = {}

    class Child(Component):
        def render(self) -> object:
            log.append("Child render")
            return create_element("span", {"text": "c"})

    class Parent(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            box["child_ref"] = create_ref()

        def shouldComponentUpdate(self, _np: object, _ns: object) -> bool:  # noqa: N802
            return False

        def componentDidMount(self) -> None:  # noqa: N802
            box["inst"] = self

        def render(self) -> object:
            log.append("Parent render")
            return create_element(Child, {"ref": box["child_ref"]})

    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        with act(flush=root.flush):
            root.render(create_element(Parent))
        assert log == ["Parent render", "Child render"]
        log.clear()

        with act(flush=root.flush):
            box["inst"].set_state({"x": 1})
        assert log == []

        with act(flush=root.flush):
            cast(Any, box["child_ref"].current).set_state({"x": 1})
        assert log == ["Child render"]
    finally:
        set_act_environment_enabled(False)


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

    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        with act(flush=root.flush):
            root.render(create_element(Top))
        assert log == ["Middle", "Bottom", "Middle"]
    finally:
        set_act_environment_enabled(False)


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
            return create_element("span", {"text": str(self.state["x"])})

    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        with act(flush=root.flush):
            root.render(create_element(A, {"x": 1}))
        assert log == []

        with act(flush=root.flush):
            root.render(create_element(A, {"x": 2}))
        assert log == ["Callback"]
    finally:
        set_act_environment_enabled(False)


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
            return create_element("span", {"text": str(self.props["text"])})

    root = create_noop_root()

    def render_editor() -> None:
        def on_change(new_props: dict[str, Any]) -> None:
            on_change_called["v"] = True
            props_box.update(new_props)
            render_editor()

        root.render(
            create_element(
                Editor,
                {"onChange": on_change, "text": props_box["text"], "rendered": props_box["rendered"]},
            )
        )

    set_act_environment_enabled(True)
    try:
        with act(flush=root.flush):
            render_editor()
        assert log == ["Mount"]

        props_box["text"] = "goodbye"
        with act(flush=root.flush):
            render_editor()
        assert log == ["Mount"]
        assert _snap_text(root) == "goodbye"
        assert on_change_called["v"]
    finally:
        set_act_environment_enabled(False)


def _snap_text(root: Any) -> str:
    snap = root.get_children_snapshot()
    if isinstance(snap, dict):
        return str(snap.get("props", {}).get("text", snap))
    return str(snap)
