# Translated from:
# - packages/react-dom/src/__tests__/ReactDOMLegacyFiber-test.js
# - packages/react-dom/src/__tests__/ReactLegacyUpdates-test.js (purge / mount slice)
# Burndown v154: legacy fiber portals, findDOMNode, host children, container warnings.
from __future__ import annotations

from collections.abc import Iterator
from typing import Any, cast

import pytest
from ryact import Component, create_element, create_portal, create_ref, fragment
from ryact.dev import is_dev, set_dev
from ryact_dom.dom import Container, ElementNode, TextNode
from ryact_dom.dom_internals import find_dom_node, reset_component_dom_registry
from ryact_dom.legacy_mount import (
    batched_updates,
    legacy_render,
    reset_legacy_mount_state,
    unmount_component_at_node,
)
from ryact_dom.root import create_root
from ryact_testkit import WarningCapture, act, set_act_environment_enabled


@pytest.fixture(autouse=True)
def _dev_and_legacy_state() -> Iterator[None]:
    prev = is_dev()
    set_dev(True)
    reset_legacy_mount_state()
    reset_component_dom_registry()
    yield
    reset_legacy_mount_state()
    reset_component_dom_registry()
    from ryact_dom.legacy_mount import _LEGACY_ROOT_BY_CONTAINER

    for root in list(_LEGACY_ROOT_BY_CONTAINER.values()):
        rr = getattr(root, "_reconciler_root", None)
        if rr is not None:
            rr._is_batching_updates = False  # type: ignore[attr-defined]
    set_dev(prev)


# --- ReactDOMLegacyFiber ---


def test_should_render_strings_as_children() -> None:
    c = Container()
    legacy_render(create_element("div", None, "hello"), c)
    assert c.text_content == "hello"


def test_should_render_numbers_as_children() -> None:
    c = Container()
    legacy_render(create_element("div", None, 42), c)
    assert c.text_content == "42"


def test_should_render_a_component_returning_strings_directly_from_render() -> None:
    class Comp(Component):
        def render(self) -> object:
            return "hello"

    c = Container()
    legacy_render(create_element(Comp), c)
    assert c.text_content == "hello"


def test_should_render_a_component_returning_numbers_directly_from_render() -> None:
    class Comp(Component):
        def render(self) -> object:
            return 42

    c = Container()
    legacy_render(create_element(Comp), c)
    assert c.text_content == "42"


def test_renders_an_empty_fragment() -> None:
    c = Container()
    legacy_render(create_element("div", None, fragment()), c)
    assert c.text_content == ""


def test_should_not_warn_when_rendering_into_an_empty_container() -> None:
    c = Container()
    with WarningCapture() as cap:
        legacy_render(create_element("div", None, "hi"), c)
    assert not any("without using React" in str(r.message) for r in cap.records)


def test_should_warn_when_doing_an_update_to_a_container_manually_cleared_outside_of_react() -> None:
    c = Container()
    legacy_render(create_element("div", None, "hi"), c)
    c.root.children.clear()
    with WarningCapture() as cap:
        legacy_render(create_element("div", None, "bye"), c)
    assert any("removed without using React" in str(r.message) for r in cap.records)


def test_should_warn_when_doing_an_update_to_a_container_manually_updated_outside_of_react() -> None:
    c = Container()
    legacy_render(create_element("div", None, "hi"), c)
    c.root.append_child(ElementNode(tag="p"))
    with WarningCapture() as cap:
        legacy_render(create_element("div", None, "bye"), c)
    assert any("updated without using React" in str(r.message) for r in cap.records)


def test_should_warn_with_a_special_message_for_false_event_listeners() -> None:
    c = Container()
    with WarningCapture() as cap:
        legacy_render(create_element("div", {"onClick": False}), c)
    assert any("value of `false`" in str(r.message) for r in cap.records)


def test_should_throw_on_bad_create_portal_argument() -> None:
    with pytest.raises(TypeError, match="Target container is not a DOM element"):
        create_portal(children=create_element("div"), container=[])  # type: ignore[arg-type]


def test_finds_the_dom_text_node_of_a_string_child() -> None:
    class Comp(Component):
        def render(self) -> object:
            return create_element("div", None, "text")

    c = Container()
    inst_ref = create_ref()
    legacy_render(create_element(Comp, {"ref": inst_ref}), c)
    node = find_dom_node(cast(Comp, inst_ref.current))
    assert isinstance(node, (ElementNode, TextNode))


def test_find_dom_node_should_find_dom_element_after_expanding_a_fragment() -> None:
    class Comp(Component):
        def render(self) -> object:
            return fragment(create_element("span", None, "x"))

    c = Container()
    inst_ref = create_ref()
    legacy_render(create_element(Comp, {"ref": inst_ref}), c)
    node = find_dom_node(cast(Comp, inst_ref.current))
    assert isinstance(node, ElementNode)
    assert node.tag.lower() == "span"


def test_finds_the_first_child_when_a_component_returns_a_fragment() -> None:
    class Comp(Component):
        def render(self) -> object:
            return fragment(create_element("span", None, "a"), create_element("span", None, "b"))

    c = Container()
    inst_ref = create_ref()
    legacy_render(create_element(Comp, {"ref": inst_ref}), c)
    node = find_dom_node(cast(Comp, inst_ref.current))
    assert isinstance(node, ElementNode)
    assert c.text_content == "ab"


def test_should_be_called_a_callback_argument() -> None:
    calls: list[int] = []

    def callback() -> None:
        calls.append(1)

    c = Container()
    legacy_render(create_element("div"), c, callback)
    assert calls == [1]


def test_should_call_a_callback_argument_when_the_same_element_is_re_rendered() -> None:
    calls: list[int] = []

    def callback() -> None:
        calls.append(1)

    c = Container()
    legacy_render(create_element("div"), c, callback)
    legacy_render(create_element("div"), c, callback)
    assert calls == [1, 1]


def test_should_render_nested_portals() -> None:
    host = Container()
    outer = Container()
    inner = Container()
    root = create_root(host)
    set_act_environment_enabled(True)
    try:
        with act():
            root.render(
                create_element(
                    "div",
                    None,
                    create_portal(
                        children=create_portal(
                            children=create_element("span", None, "nested"),
                            container=inner,
                        ),
                        container=outer,
                    ),
                )
            )
        assert inner.text_content == "nested"
        with act():
            root.unmount()
        assert inner.root.children == []
        assert outer.root.children == []
    finally:
        set_act_environment_enabled(False)


def test_should_render_many_portals() -> None:
    host = Container()
    portals = [Container() for _ in range(3)]
    root = create_root(host)
    set_act_environment_enabled(True)
    try:
        with act():
            root.render(
                create_element(
                    "div",
                    None,
                    *[
                        create_portal(children=create_element("span", None, str(i)), container=p)
                        for i, p in enumerate(portals)
                    ],
                )
            )
        for i, p in enumerate(portals):
            assert p.text_content == str(i)
    finally:
        set_act_environment_enabled(False)


def test_unmounted_legacy_roots_should_never_clear_newer_root_content_from_a_container() -> None:
    c = Container()
    legacy_render(create_element("div", None, "legacy"), c)
    unmount_component_at_node(c)
    root = create_root(c)
    set_act_environment_enabled(True)
    try:
        with act():
            root.render(create_element("div", None, "modern"))
        assert c.text_content == "modern"
        with act():
            unmount_component_at_node(c)
        assert c.text_content == "modern"
    finally:
        set_act_environment_enabled(False)


# --- ReactLegacyUpdates (instance purge) ---


def test_mounts_and_unmounts_are_sync_even_in_a_batch() -> None:
    log: list[str] = []

    class Child(Component):
        def componentDidMount(self) -> None:  # noqa: N802
            log.append("mount")

        def componentWillUnmount(self) -> None:  # noqa: N802
            log.append("unmount")

        def render(self) -> object:
            return create_element("span", None, "c")

    class Parent(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self._state = {"show": True}

        def render(self) -> object:
            if self.state["show"]:
                return create_element(Child)
            return create_element("span", None, "x")

    c = Container()
    parent = legacy_render(create_element(Parent), c)
    log.clear()

    def batch() -> None:
        parent.set_state({"show": False})
        parent.set_state({"show": True})

    batched_updates(batch)
    assert log == ["unmount", "mount"]
    assert c.text_content == "c"


def test_does_not_call_render_after_a_component_has_been_deleted() -> None:
    log: list[str] = []
    comp_a: dict[str, Any] = {}
    comp_b: dict[str, Any] = {}

    class B(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self._state = {"updates": 0}

        def componentDidMount(self) -> None:  # noqa: N802
            comp_b["inst"] = self

        def render(self) -> object:
            log.append("B")
            return create_element("span", None, "b")

    class A(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self._state = {"showB": True}

        def componentDidMount(self) -> None:  # noqa: N802
            comp_a["inst"] = self

        def render(self) -> object:
            if self.state["showB"]:
                return create_element(B)
            return create_element("span", None, "x")

    c = Container()
    legacy_render(create_element(A), c)
    assert log == ["B"]
    log.clear()

    def batch() -> None:
        comp_b["inst"].set_state({"updates": 1})
        comp_a["inst"].set_state({"showB": False})

    batched_updates(batch)
    assert log == []
