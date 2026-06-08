# Translated from: packages/react-dom/src/__tests__/ReactDOMLegacyFiber-test.js
# Burndown v166: Offscreen legacy mount, portal context, relatedTarget enter/leave.
from __future__ import annotations

from collections.abc import Iterator
from typing import Any, cast

import pytest
from ryact import Component, Offscreen, create_element, create_portal, create_ref
from ryact.dev import is_dev, set_dev
from ryact_dom.dom import Container, ElementNode
from ryact_dom.dom_internals import reset_component_dom_registry
from ryact_dom.legacy_mount import legacy_render, reset_legacy_mount_state
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
    set_dev(prev)


def _simulate_mouse_move(
    *,
    from_node: ElementNode | None,
    to_node: ElementNode | None,
) -> None:
    if from_node is not None:
        from_node.dispatch_event("mouseout", related_target=to_node)
    if to_node is not None:
        to_node.dispatch_event("mouseover", related_target=from_node)


def test_should_not_crash_encountering_low_priority_tree() -> None:
    c = Container()
    legacy_render(
        create_element(
            "div",
            None,
            create_element(Offscreen, {"mode": "hidden"}, create_element("span", None, "x")),
        ),
        c,
    )


def test_should_pass_portal_context_when_rendering_subtree_elsewhere() -> None:
    portal_c = Container()
    host_c = Container()

    class ContextChild(Component):
        contextTypes = {"foo": object}  # type: ignore[attr-defined]

        def render(self) -> object:
            return create_element("span", None, str(self.context.get("foo", "")))

    class Parent(Component):
        childContextTypes = {"foo": object}  # type: ignore[attr-defined]

        def getChildContext(self) -> dict[str, str]:  # noqa: N802
            return {"foo": "bar"}

        def render(self) -> object:
            return create_portal(children=create_element(ContextChild), container=portal_c)

    with WarningCapture():
        legacy_render(create_element(Parent), host_c)
    assert host_c.text_content == ""
    assert portal_c.text_content == "bar"


def test_should_update_portal_context_if_it_changes_due_to_setstate() -> None:
    portal_c = Container()
    host_c = Container()
    parent_box: dict[str, Any] = {}

    class ContextChild(Component):
        contextTypes = {"foo": object, "getFoo": object}  # type: ignore[attr-defined]

        def render(self) -> object:
            get_foo = self.context.get("getFoo")
            foo = self.context.get("foo", "")
            suffix = get_foo() if callable(get_foo) else foo
            return create_element("span", None, f"{foo}-{suffix}")

    class Parent(Component):
        childContextTypes = {"foo": object, "getFoo": object}  # type: ignore[attr-defined]

        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self._state = {"bar": "initial"}

        def getChildContext(self) -> dict[str, object]:  # noqa: N802
            return {"foo": self.state["bar"], "getFoo": lambda: self.state["bar"]}

        def render(self) -> object:
            return create_portal(children=create_element(ContextChild), container=portal_c)

    with WarningCapture():
        legacy_render(
            create_element(Parent, {"ref": lambda inst: parent_box.setdefault("inst", inst)}),
            host_c,
        )
    assert portal_c.text_content == "initial-initial"
    parent = cast(Component, parent_box["inst"])
    parent.set_state({"bar": "changed"})
    assert portal_c.text_content == "changed-changed"


def test_should_update_portal_context_if_it_changes_due_to_re_render() -> None:
    portal_c = Container()
    host_c = Container()

    class ContextChild(Component):
        contextTypes = {"foo": object, "getFoo": object}  # type: ignore[attr-defined]

        def render(self) -> object:
            get_foo = self.context.get("getFoo")
            foo = self.context.get("foo", "")
            suffix = get_foo() if callable(get_foo) else foo
            return create_element("span", None, f"{foo}-{suffix}")

    class Parent(Component):
        childContextTypes = {"foo": object, "getFoo": object}  # type: ignore[attr-defined]

        def getChildContext(self) -> dict[str, object]:  # noqa: N802
            bar = str(self.props.get("bar", "initial"))
            return {"foo": bar, "getFoo": lambda: bar}

        def render(self) -> object:
            return create_portal(children=create_element(ContextChild), container=portal_c)

    with WarningCapture():
        legacy_render(create_element(Parent, {"bar": "initial"}), host_c)
    assert portal_c.text_content == "initial-initial"
    with WarningCapture():
        legacy_render(create_element(Parent, {"bar": "changed"}), host_c)
    assert portal_c.text_content == "changed-changed"


def test_should_not_onmouseleave_when_staying_in_the_portal() -> None:
    portal_c = Container()
    host_c = Container()
    ops: list[str] = []
    first = create_ref()
    second = create_ref()
    third = create_ref()

    legacy_render(
        create_element(
            "div",
            None,
            create_element(
                "div",
                {
                    "onMouseEnter": lambda _e: ops.append("enter parent"),
                    "onMouseLeave": lambda _e: ops.append("leave parent"),
                },
                create_element("div", {"ref": first}, "one"),
                create_portal(
                    children=create_element(
                        "div",
                        {
                            "ref": second,
                            "onMouseEnter": lambda _e: ops.append("enter portal"),
                            "onMouseLeave": lambda _e: ops.append("leave portal"),
                        },
                        "portal",
                    ),
                    container=portal_c,
                ),
            ),
            create_element("div", {"ref": third}, "three"),
        ),
        host_c,
    )
    first_node = cast(ElementNode, first.current)
    second_node = cast(ElementNode, second.current)
    third_node = cast(ElementNode, third.current)

    _simulate_mouse_move(from_node=None, to_node=first_node)
    assert ops == ["enter parent"]
    ops.clear()

    _simulate_mouse_move(from_node=first_node, to_node=second_node)
    assert ops == ["enter portal"]
    ops.clear()

    _simulate_mouse_move(from_node=second_node, to_node=third_node)
    assert ops == ["leave portal", "leave parent"]


def test_does_not_fire_mouseenter_twice_when_relatedtarget_is_the_root_node() -> None:
    c = Container()
    ops: list[str] = []
    target = create_ref()

    legacy_render(
        create_element(
            "div",
            {
                "ref": target,
                "onMouseEnter": lambda _e: ops.append("enter"),
                "onMouseLeave": lambda _e: ops.append("leave"),
            },
            "child",
        ),
        c,
    )
    target_node = cast(ElementNode, target.current)
    root_node = c.root

    _simulate_mouse_move(from_node=None, to_node=root_node)
    assert ops == []
    ops.clear()

    _simulate_mouse_move(from_node=root_node, to_node=target_node)
    assert ops == ["enter"]
    ops.clear()

    _simulate_mouse_move(from_node=target_node, to_node=root_node)
    assert ops == ["leave"]
    ops.clear()

    _simulate_mouse_move(from_node=root_node, to_node=None)
    assert ops == []
