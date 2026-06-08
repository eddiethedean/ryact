# Translated from: packages/react-dom/src/__tests__/ReactLegacyCompositeComponent-test.js
# Burndown v163: legacy context propagation on class composite components.
from __future__ import annotations

from collections.abc import Iterator
from typing import Any, cast

import pytest
from ryact import Component, create_element, create_ref
from ryact.children import only_child
from ryact.dev import is_dev, set_dev
from ryact_dom.dom import Container, ElementNode, TextNode
from ryact_dom.dom_internals import find_dom_node, reset_component_dom_registry
from ryact_dom.legacy_mount import legacy_render, reset_legacy_mount_state
from ryact_dom.root import create_root
from ryact_testkit import WarningCapture, act


@pytest.fixture(autouse=True)
def _dev_and_reset() -> Iterator[None]:
    prev = is_dev()
    set_dev(True)
    reset_legacy_mount_state()
    reset_component_dom_registry()
    yield
    reset_legacy_mount_state()
    reset_component_dom_registry()
    set_dev(prev)


def _host(container: Container) -> ElementNode:
    for ch in container.root.children:
        if isinstance(ch, ElementNode):
            return ch
    raise AssertionError("expected host child")


def _dom_text(node: ElementNode | TextNode | None) -> str:
    if node is None:
        return ""
    if isinstance(node, TextNode):
        return node.text
    return "".join(_dom_text(ch) if isinstance(ch, (ElementNode, TextNode)) else "" for ch in node.children)


def test_context_should_be_passed_down_from_the_parent() -> None:
    class Parent(Component):
        childContextTypes = {"foo": object}  # type: ignore[attr-defined]

        def getChildContext(self) -> dict[str, str]:  # noqa: N802
            return {"foo": "bar"}

        def render(self) -> object:
            return create_element(Child)

    class Child(Component):
        contextTypes = {"foo": object}  # type: ignore[attr-defined]

        def render(self) -> object:
            return create_element("span", None, str(self.context.get("foo", "")))

    c = Container()
    with WarningCapture() as cap:
        legacy_render(create_element(Parent), c)
    assert any("childContextTypes" in str(r.message) for r in cap.records)
    assert any("contextTypes" in str(r.message) for r in cap.records)


def test_should_pass_context_to_children_when_not_owner() -> None:
    class Grandchild(Component):
        contextTypes = {"foo": object}  # type: ignore[attr-defined]

        def render(self) -> object:
            return create_element("span", None, str(self.context.get("foo", "")))

    class Child(Component):
        childContextTypes = {"foo": object}  # type: ignore[attr-defined]

        def getChildContext(self) -> dict[str, str]:  # noqa: N802
            return {"foo": "bar"}

        def render(self) -> object:
            return only_child(self.props.get("children"))

    class Parent(Component):
        def render(self) -> object:
            return create_element(Child, None, create_element(Grandchild))

    c = Container()
    root = create_root(c)
    with WarningCapture(), act():
        root.render(create_element(Parent))
    assert c.text_content == "bar"


def test_should_pass_context_when_rerendered_for_static_child() -> None:
    parent_box: dict[str, Any] = {}
    child_box: dict[str, Any] = {}

    class Parent(Component):
        childContextTypes = {"foo": object, "flag": object}  # type: ignore[attr-defined]

        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self._state = {"flag": False}

        def getChildContext(self) -> dict[str, object]:  # noqa: N802
            return {"foo": "bar", "flag": self.state["flag"]}

        def render(self) -> object:
            return only_child(self.props.get("children"))

    class Middle(Component):
        def render(self) -> object:
            return self.props.get("children")

    class Child(Component):
        contextTypes = {"foo": object, "flag": object}  # type: ignore[attr-defined]

        def render(self) -> object:
            child_box["inst"] = self
            return create_element("span", None, "Child")

    c = Container()
    root = create_root(c)
    with WarningCapture(), act():
        root.render(
            create_element(
                Parent,
                {"ref": lambda inst: parent_box.setdefault("inst", inst)},
                create_element(Middle, None, create_element(Child)),
            )
        )
    parent = cast(Component, parent_box["inst"])
    child = cast(Component, child_box["inst"])
    assert parent.state["flag"] is False
    assert child.context == {"foo": "bar", "flag": False}
    with act():
        parent.set_state({"flag": True})
    assert parent.state["flag"] is True
    assert child.context == {"foo": "bar", "flag": True}


def test_should_pass_context_when_rerendered_for_static_child_within_a_composite_component() -> None:
    wrapper_box: dict[str, Any] = {}

    class Parent(Component):
        childContextTypes = {"flag": object}  # type: ignore[attr-defined]

        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self._state = {"flag": True}

        def getChildContext(self) -> dict[str, bool]:  # noqa: N802
            return {"flag": bool(self.state["flag"])}

        def render(self) -> object:
            return self.props.get("children")

    class Child(Component):
        contextTypes = {"flag": object}  # type: ignore[attr-defined]

        def render(self) -> object:
            return create_element("span", None, str(self.context.get("flag")))

    class Wrapper(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self.parent_ref = create_ref()
            self.child_ref = create_ref()

        def render(self) -> object:
            return create_element(
                "div",
                None,
                create_element(Parent, {"ref": self.parent_ref}, create_element(Child, {"ref": self.child_ref})),
            )

    c = Container()
    root = create_root(c)
    with WarningCapture(), act():
        root.render(create_element(Wrapper, {"ref": lambda inst: wrapper_box.setdefault("inst", inst)}))
    wrapper = cast(Wrapper, wrapper_box["inst"])
    assert wrapper.parent_ref.current.state["flag"] is True
    assert wrapper.child_ref.current.context == {"flag": True}
    with act():
        wrapper.parent_ref.current.set_state({"flag": False})
    assert wrapper.parent_ref.current.state["flag"] is False
    assert wrapper.child_ref.current.context == {"flag": False}


def test_should_pass_context_transitively() -> None:
    child_box: dict[str, Any] = {}
    grandchild_box: dict[str, Any] = {}

    class Parent(Component):
        childContextTypes = {"foo": object, "depth": object}  # type: ignore[attr-defined]

        def getChildContext(self) -> dict[str, object]:  # noqa: N802
            return {"foo": "bar", "depth": 0}

        def render(self) -> object:
            return create_element(Child)

    class Child(Component):
        contextTypes = {"foo": object, "depth": object}  # type: ignore[attr-defined]
        childContextTypes = {"depth": object}  # type: ignore[attr-defined]

        def getChildContext(self) -> dict[str, int]:  # noqa: N802
            return {"depth": int(self.context.get("depth", 0)) + 1}

        def render(self) -> object:
            child_box["inst"] = self
            return create_element(Grandchild)

    class Grandchild(Component):
        contextTypes = {"foo": object, "depth": object}  # type: ignore[attr-defined]

        def render(self) -> object:
            grandchild_box["inst"] = self
            return create_element("span", None, "x")

    c = Container()
    root = create_root(c)
    with WarningCapture(), act():
        root.render(create_element(Parent))
    assert child_box["inst"].context == {"foo": "bar", "depth": 0}
    assert grandchild_box["inst"].context == {"foo": "bar", "depth": 1}


def test_should_pass_context_when_rerendered() -> None:
    parent_box: dict[str, Any] = {}
    child_box: dict[str, Any] = {}

    class Parent(Component):
        childContextTypes = {"foo": object, "depth": object}  # type: ignore[attr-defined]

        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self._state = {"flag": False}

        def getChildContext(self) -> dict[str, object]:  # noqa: N802
            return {"foo": "bar", "depth": 0}

        def render(self) -> object:
            output: object = create_element("span", None, "empty")
            if self.state["flag"]:
                output = create_element(Child)
            return output

    class Child(Component):
        contextTypes = {"foo": object, "depth": object}  # type: ignore[attr-defined]

        def render(self) -> object:
            child_box["inst"] = self
            return create_element("span", None, "Child")

    c = Container()
    root = create_root(c)
    with WarningCapture(), act():
        root.render(create_element(Parent, {"ref": lambda inst: parent_box.setdefault("inst", inst)}))
    assert child_box.get("inst") is None
    parent = cast(Component, parent_box["inst"])
    assert parent.state["flag"] is False
    with act():
        parent.set_state({"flag": True})
    assert parent.state["flag"] is True
    assert child_box["inst"].context == {"foo": "bar", "depth": 0}


def test_unmasked_context_propagates_through_updates() -> None:
    class Leaf(Component):
        contextTypes = {"foo": object}  # type: ignore[attr-defined]

        def UNSAFE_componentWillReceiveProps(self, _np: object, next_context: dict[str, object]) -> None:  # noqa: N802
            assert "foo" in next_context

        def shouldComponentUpdate(self, _np: object, _ns: object, next_context: dict[str, object]) -> bool:  # noqa: N802
            assert "foo" in next_context
            return True

        def render(self) -> object:
            return create_element("span", None, str(self.context.get("foo", "")))

    class Intermediary(Component):
        def UNSAFE_componentWillReceiveProps(self, _np: object, next_context: dict[str, object]) -> None:  # noqa: N802
            assert "foo" not in next_context

        def shouldComponentUpdate(self, _np: object, _ns: object, next_context: dict[str, object]) -> bool:  # noqa: N802
            assert "foo" not in next_context
            return True

        def render(self) -> object:
            return create_element(Leaf)

    class Parent(Component):
        childContextTypes = {"foo": object}  # type: ignore[attr-defined]

        def getChildContext(self) -> dict[str, str]:  # noqa: N802
            return {"foo": str(self.props.get("cntxt", ""))}

        def render(self) -> object:
            return create_element(Intermediary)

    c = Container()
    with WarningCapture():
        legacy_render(create_element(Parent, {"cntxt": "noise"}), c)
    assert c.text_content == "noise"
    host = _host(c)
    host.props["id"] = "aliens"
    assert host.props.get("id") == "aliens"
    with WarningCapture():
        legacy_render(create_element(Parent, {"cntxt": "bar"}), c)
    assert c.text_content == "bar"
    assert _host(c).props.get("id") == "aliens"


def test_should_trigger_componentwillreceiveprops_for_context_changes() -> None:
    context_changes = 0
    prop_changes = 0

    class GrandChild(Component):
        contextTypes = {"foo": object}  # type: ignore[attr-defined]

        def UNSAFE_componentWillReceiveProps(self, next_props: object, next_context: dict[str, object]) -> None:  # noqa: N802
            nonlocal context_changes, prop_changes
            assert "foo" in next_context
            if next_props is not self._props:
                prop_changes += 1
            if next_context is not self.context:
                context_changes += 1

        def render(self) -> object:
            return self.props.get("children")

    class ChildWithContext(Component):
        contextTypes = {"foo": object}  # type: ignore[attr-defined]

        def UNSAFE_componentWillReceiveProps(self, next_props: object, next_context: dict[str, object]) -> None:  # noqa: N802
            nonlocal context_changes, prop_changes
            assert "foo" in next_context
            if next_props is not self._props:
                prop_changes += 1
            if next_context is not self.context:
                context_changes += 1

        def render(self) -> object:
            return self.props.get("children")

    class ChildWithoutContext(Component):
        def UNSAFE_componentWillReceiveProps(self, next_props: object, next_context: dict[str, object]) -> None:  # noqa: N802
            nonlocal context_changes, prop_changes
            assert "foo" not in next_context
            if next_props is not self._props:
                prop_changes += 1
            if next_context is not self.context:
                context_changes += 1

        def render(self) -> object:
            return self.props.get("children")

    class Parent(Component):
        childContextTypes = {"foo": object}  # type: ignore[attr-defined]

        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self._state = {"foo": "abc"}

        def getChildContext(self) -> dict[str, str]:  # noqa: N802
            return {"foo": str(self.state["foo"])}

        def render(self) -> object:
            return self.props.get("children")

    parent_children = create_element(
        "div",
        None,
        create_element(
            ChildWithContext,
            None,
            create_element(GrandChild, None, "A1"),
            create_element(GrandChild, None, "A2"),
        ),
        create_element(
            ChildWithoutContext,
            None,
            create_element(GrandChild, None, "B1"),
            create_element(GrandChild, None, "B2"),
        ),
    )

    parent_box: dict[str, Any] = {}
    c = Container()
    with WarningCapture():
        legacy_render(
            create_element(
                Parent,
                {"ref": lambda inst: parent_box.setdefault("inst", inst), "children": parent_children},
            ),
            c,
        )
    parent = cast(Component, parent_box["inst"])
    parent.set_state({"foo": "def"})
    assert prop_changes == 0
    assert context_changes == 3


def test_should_update_refs_if_shouldcomponentupdate_gives_false_in_legacy_mode() -> None:
    class Static(Component):
        def shouldComponentUpdate(self, _np: object, _ns: object) -> bool:  # noqa: N802
            return False

        def render(self) -> object:
            ch = self.props.get("children", "")
            if isinstance(ch, (list, tuple)):
                ch = only_child(ch) if ch else ""
            return create_element("span", None, str(ch))

    class ComponentWithRefs(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self.static0_ref = create_ref()
            self.static1_ref = create_ref()

        def render(self) -> object:
            if self.props.get("flipped"):
                return create_element(
                    "div",
                    None,
                    create_element(Static, {"ref": self.static0_ref, "children": "B (ignored)"}),
                    create_element(Static, {"ref": self.static1_ref, "children": "A (ignored)"}),
                )
            return create_element(
                "div",
                None,
                create_element(Static, {"ref": self.static0_ref, "children": "A"}),
                create_element(Static, {"ref": self.static1_ref, "children": "B"}),
            )

    c = Container()
    comp = legacy_render(create_element(ComponentWithRefs, {"flipped": False}), c)
    assert _dom_text(find_dom_node(comp.static0_ref.current)) == "A"
    assert _dom_text(find_dom_node(comp.static1_ref.current)) == "B"
    legacy_render(create_element(ComponentWithRefs, {"flipped": True}), c)
    assert _dom_text(find_dom_node(comp.static0_ref.current)) == "B"
    assert _dom_text(find_dom_node(comp.static1_ref.current)) == "A"
