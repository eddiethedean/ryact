# Translated from:
# - packages/react-dom/src/__tests__/ReactLegacyMount-test.js
# - packages/react-dom/src/__tests__/ReactLegacyCompositeComponent-test.js
# - packages/react-dom/src/__tests__/ReactCompositeComponentDOMMinimalism-test.js
# Burndown v152: legacy render/unmount, batched legacy roots, composite + DOM minimalism.
from __future__ import annotations

from collections.abc import Iterator
from typing import Any, cast

import pytest
from ryact import Component, create_element, create_ref
from ryact.dev import is_dev, set_dev
from ryact_dom.dom import Container, ElementNode, TextNode
from ryact_dom.dom_internals import find_dom_node, reset_component_dom_registry
from ryact_dom.legacy_mount import (
    batched_updates,
    legacy_render,
    reset_legacy_mount_state,
    unmount_component_at_node,
)
from ryact_dom.root import create_root, render_into
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


def _host(container: Container) -> ElementNode:
    for ch in container.root.children:
        if isinstance(ch, ElementNode):
            return ch
    raise AssertionError("expected a host child")


def _element_children(host: ElementNode) -> list[ElementNode]:
    return [ch for ch in host.children if isinstance(ch, ElementNode)]


# --- ReactLegacyMount ---


def test_throws_when_given_a_non_node() -> None:
    with pytest.raises(TypeError, match="Target container is not a DOM element"):
        unmount_component_at_node([])  # type: ignore[arg-type]


def test_returns_false_on_non_react_containers() -> None:
    c = Container()
    c.root.append_child(ElementNode(tag="b"))
    cast(ElementNode, c.root.children[0]).append_child(TextNode(text="hellooo"))
    assert unmount_component_at_node(c) is False
    assert c.text_content == "hellooo"


def test_returns_true_on_react_containers() -> None:
    c = Container()
    legacy_render(create_element("b", None, "hellooo"), c)
    assert c.text_content == "hellooo"
    assert unmount_component_at_node(c) is True
    assert c.text_content == ""


def test_warns_when_given_a_factory() -> None:
    class Comp(Component):
        def render(self) -> object:
            return create_element("div")

    c = Container()
    with WarningCapture() as cap:
        legacy_render(Comp, c)  # type: ignore[arg-type]
    assert any("Functions are not valid as a React child" in str(r.message) for r in cap.records)


def test_should_render_different_components_in_same_root() -> None:
    c = Container()
    legacy_render(create_element("div"), c)
    assert _host(c).tagName.upper() == "DIV"
    legacy_render(create_element("span"), c)
    assert _host(c).tagName.upper() == "SPAN"


def test_should_unmount_and_remount_if_the_key_changes() -> None:
    log: list[str] = []

    class Comp(Component):
        def componentDidMount(self) -> None:  # noqa: N802
            log.append("mount")

        def componentWillUnmount(self) -> None:  # noqa: N802
            log.append("unmount")

        def render(self) -> object:
            return create_element("span", None, str(self.props.get("text", "")))

    c = Container()
    legacy_render(create_element(Comp, {"text": "orange"}, key="A"), c)
    assert c.text_content == "orange"
    assert log == ["mount"]
    legacy_render(create_element(Comp, {"text": "green"}, key="B"), c)
    assert c.text_content == "green"
    assert log == ["mount", "unmount", "mount"]
    legacy_render(create_element(Comp, {"text": "blue"}, key="B"), c)
    assert c.text_content == "blue"
    assert log == ["mount", "unmount", "mount"]


def test_should_reuse_markup_if_rendering_to_the_same_target_twice() -> None:
    c = Container()
    r1 = legacy_render(create_element("div"), c)
    r2 = legacy_render(create_element("div"), c)
    assert r1 is r2


def test_should_not_warn_if_mounting_into_non_empty_node() -> None:
    c = Container()
    c.root.append_child(ElementNode(tag="div"))
    with WarningCapture() as cap:
        legacy_render(create_element("div"), c)
    assert not cap.records


def test_should_warn_when_mounting_into_document_body() -> None:
    c = Container()
    c._is_document_body = True  # type: ignore[attr-defined]
    with WarningCapture() as cap:
        legacy_render(create_element("div"), c)
    assert any("document.body" in str(r.message) for r in cap.records)


def test_should_warn_if_render_removes_react_rendered_children() -> None:
    class Outer(Component):
        def render(self) -> object:
            return create_element("div", None, create_element("div"))

    c = Container()
    legacy_render(create_element(Outer), c)
    _element_children(_host(c))[0]
    with WarningCapture() as cap:
        render_into(c, _host(c), create_element("span"))
    assert any("Replacing React-rendered children" in str(r.message) for r in cap.records)


def test_should_warn_if_unmounted_node_was_rendered_by_another_copy_of_react() -> None:
    class Outer(Component):
        def render(self) -> object:
            return create_element("div", None, create_element("div"))

    c = Container()
    legacy_render(create_element(Outer), c)
    from ryact_dom import legacy_mount as lm

    lm._LEGACY_ROOT_BY_CONTAINER.pop(id(c), None)
    with WarningCapture() as cap:
        unmount_component_at_node(c)
    assert any("another copy of React" in str(r.message) for r in cap.records)
    legacy_render(create_element(Outer), c)
    assert unmount_component_at_node(c) is True


def test_passes_the_correct_callback_context() -> None:
    c = Container()
    calls: list[str] = []

    def callback(self: Any) -> None:
        calls.append(self.nodeName)

    legacy_render(create_element("div"), c, callback)
    legacy_render(create_element("div"), c, callback)
    legacy_render(create_element("span"), c, callback)
    batched_updates(lambda: legacy_render(create_element("span"), c, callback))
    batched_updates(lambda: legacy_render(create_element("article"), c, callback))
    assert calls == ["DIV", "DIV", "SPAN", "SPAN", "ARTICLE"]


def test_initial_mount_of_legacy_root_is_sync_inside_batched_updates() -> None:
    class Foo(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self._state = {"active": False}

        def componentDidMount(self) -> None:  # noqa: N802
            self.set_state({"active": True})

        def render(self) -> object:
            ch = self.props.get("children", "")
            if isinstance(ch, (list, tuple)) and len(ch) == 1:
                ch = ch[0]
            return create_element(
                "div",
                None,
                f"{ch}{'!' if self.state['active'] else ''}",
            )

    c1 = Container()
    c2 = Container()
    legacy_render(create_element("div", None, "1"), c1)

    def batch() -> None:
        legacy_render(create_element("div", None, "2"), c1)
        legacy_render(create_element(Foo, {"children": "a"}), c2)

    batched_updates(batch)
    assert c1.text_content == "2"
    assert c2.text_content == "a!"


@pytest.mark.skip(reason="Implemented in test_dom_comment_mount_burndown_v180.py")
def test_renders_at_a_comment_node() -> None:
    pass


def test_clears_existing_children_with_legacy_api() -> None:
    c = Container()
    c.root.append_child(ElementNode(tag="div"))
    h0 = cast(ElementNode, c.root.children[0])
    h0.append_child(ElementNode(tag="div"))
    h0.append_child(ElementNode(tag="div"))
    legacy_render(
        create_element("div", None, create_element("span", None, "c"), create_element("span", None, "d")),
        c,
    )
    assert c.text_content == "cd"
    legacy_render(
        create_element("div", None, create_element("span", None, "d"), create_element("span", None, "c")),
        c,
    )
    assert c.text_content == "dc"


def test_warns_when_rendering_with_legacy_api_into_createroot_container() -> None:
    c = Container()
    root = create_root(c)
    set_act_environment_enabled(True)
    try:
        with act():
            root.render(create_element("div", None, "Hi"))
        assert c.text_content == "Hi"
        with WarningCapture() as cap:
            legacy_render(create_element("div", None, "Bye"), c)
        assert any("ReactDOMClient.createRoot" in str(r.message) for r in cap.records)
        assert c.text_content == "Bye"
    finally:
        set_act_environment_enabled(False)


def test_warns_when_unmounting_with_legacy_api_no_previous_content() -> None:
    c = Container()
    root = create_root(c)
    with act():
        root.render(create_element("div", None, "Hi"))
    with WarningCapture() as cap:
        ok = unmount_component_at_node(c)
    assert ok is False
    assert any("ReactDOMClient.createRoot" in str(r.message) for r in cap.records)
    assert c.text_content == "Hi"
    with act():
        root.unmount()
    assert c.text_content == ""


def test_warns_when_unmounting_with_legacy_api_has_previous_content() -> None:
    c = Container()
    c.root.append_child(ElementNode(tag="div"))
    root = create_root(c)
    with act():
        root.render(create_element("div", None, "Hi"))
    with WarningCapture() as cap:
        ok = unmount_component_at_node(c)
    assert ok is False
    assert any("ReactDOMClient.createRoot" in str(r.message) for r in cap.records)
    with act():
        root.unmount()


def test_warns_when_passing_legacy_container_to_create_root() -> None:
    c = Container()
    legacy_render(create_element("div", None, "Hi"), c)
    with WarningCapture() as cap:
        create_root(c)
    assert any("ReactDOM.render" in str(r.message) for r in cap.records)


# --- ReactLegacyCompositeComponent ---


def test_should_warn_about_set_state_in_render_in_legacy_mode() -> None:
    render_passes = 0
    rendered_state = -1

    class Comp(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self._state = {"value": 0}

        def render(self) -> object:
            nonlocal render_passes, rendered_state
            render_passes += 1
            rendered_state = self.state["value"]
            if self.state["value"] == 0:
                self.set_state({"value": 1})
            return create_element("div")

    c = Container()
    inst_ref = create_ref()
    with WarningCapture() as cap:
        legacy_render(create_element(Comp, {"ref": inst_ref}), c)
        legacy_render(create_element(Comp, {"prop": 123, "ref": inst_ref}), c)
    inst = cast(Comp, inst_ref.current)
    assert any("Cannot update during an existing state transition" in str(r.message) for r in cap.records)
    assert render_passes in (2, 3, 4)
    assert rendered_state == 1
    assert inst.state["value"] == 1


def test_only_renders_once_if_updated_in_componentwillreceiveprops_in_legacy_mode() -> None:
    renders = 0

    class Comp(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self._state = {"updated": False}

        def UNSAFE_componentWillReceiveProps(self, props: object) -> None:  # noqa: N802
            assert cast(dict[str, Any], props)["update"] == 1
            assert renders == 1
            self.set_state({"updated": True})
            assert renders == 1

        def render(self) -> object:
            nonlocal renders
            renders += 1
            return create_element("div")

    c = Container()
    inst_ref = create_ref()
    legacy_render(create_element(Comp, {"update": 0, "ref": inst_ref}), c)
    inst = cast(Comp, inst_ref.current)
    assert renders == 1
    assert inst.state["updated"] is False
    legacy_render(create_element(Comp, {"update": 1, "ref": inst_ref}), c)
    assert renders == 2
    assert inst.state["updated"] is True


def test_only_renders_once_if_updated_in_cwrp_when_batching_in_legacy_mode() -> None:
    renders = 0

    class Comp(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self._state = {"updated": False}

        def UNSAFE_componentWillReceiveProps(self, props: object) -> None:  # noqa: N802
            assert cast(dict[str, Any], props)["update"] == 1
            assert renders == 1
            self.set_state({"updated": True})
            assert renders == 1

        def render(self) -> object:
            nonlocal renders
            renders += 1
            return create_element("div")

    c = Container()
    inst_ref = create_ref()
    legacy_render(create_element(Comp, {"update": 0, "ref": inst_ref}), c)
    inst = cast(Comp, inst_ref.current)
    batched_updates(lambda: legacy_render(create_element(Comp, {"update": 1, "ref": inst_ref}), c))
    assert renders == 2
    assert inst.state["updated"] is True


def test_should_allow_access_to_find_dom_node_in_componentwillunmount_in_legacy_mode() -> None:
    seen: list[ElementNode | None] = []

    class Comp(Component):
        def componentDidMount(self) -> None:  # noqa: N802
            seen.append(find_dom_node(self))

        def componentWillUnmount(self) -> None:  # noqa: N802
            seen.append(find_dom_node(self))

        def render(self) -> object:
            return create_element("div")

    c = Container()
    legacy_render(create_element(Comp), c)
    assert len(seen) == 1 and seen[0] is not None
    unmount_component_at_node(c)
    assert len(seen) == 2 and seen[0] is not None and seen[1] is not None


def test_should_not_warn_about_unmounting_during_unmounting_in_legacy_mode() -> None:
    layer = Container()

    class Inner(Component):
        def componentDidMount(self) -> None:  # noqa: N802
            legacy_render(create_element("div"), layer)

        def componentWillUnmount(self) -> None:  # noqa: N802
            unmount_component_at_node(layer)

        def render(self) -> object:
            return create_element("div")

    class Outer(Component):
        def render(self) -> object:
            return create_element("div", None, self.props.get("children"))

    c = Container()
    with WarningCapture() as cap:
        legacy_render(create_element(Outer, None, create_element(Inner)), c)
        legacy_render(create_element(Outer), c)
    assert not any("unmount" in str(r.message).lower() and "warning" in str(r.message).lower() for r in cap.records)


def test_should_replace_state_in_legacy_mode() -> None:
    class Moo(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self._state = {"x": 1}

        def render(self) -> object:
            return create_element("div")

    c = Container()
    root = create_root(c)
    moo_ref = create_ref()
    with act():
        root.render(create_element(Moo, {"ref": moo_ref}))
    moo = cast(Moo, moo_ref.current)
    moo.replace_state({"y": 2})
    with act():
        root.render(create_element(Moo, {"ref": moo_ref}))
    assert "x" not in moo.state
    assert moo.state["y"] == 2


def test_should_support_objects_with_prototypes_as_state_in_legacy_mode() -> None:
    class NotActuallyImmutable:
        def __init__(self, s: str) -> None:
            self.str = s

        def am_i_immutable(self) -> bool:
            return True

    class Moo(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self._state = NotActuallyImmutable("first")

        def render(self) -> object:
            return create_element("div")

    c = Container()
    root = create_root(c)
    moo_ref = create_ref()
    with act():
        root.render(create_element(Moo, {"ref": moo_ref}))
    moo = cast(Moo, moo_ref.current)
    assert moo.state.str == "first"
    second = NotActuallyImmutable("second")
    moo.replace_state(second)
    with act():
        root.render(create_element(Moo, {"ref": moo_ref}))
    assert moo.state is second
    moo.set_state({"str": "third"})
    with act():
        root.render(create_element(Moo, {"ref": moo_ref}))
    assert moo.state["str"] == "third"


# --- ReactCompositeComponentDOMMinimalism ---


def test_should_not_render_extra_nodes_for_non_interpolated_text() -> None:
    class Lower(Component):
        def render(self) -> object:
            return create_element("div", None, self.props.get("children"))

    class MyComposite(Component):
        def render(self) -> object:
            return create_element(Lower, None, self.props.get("children"))

    c = Container()
    with act():
        create_root(c).render(create_element(MyComposite, None, "A string child"))
    host = _host(c)
    assert host.tagName.upper() == "DIV"
    assert _element_children(host) == []


def test_should_not_render_extra_nodes_for_interpolated_text() -> None:
    class Lower(Component):
        def render(self) -> object:
            return create_element("div", None, self.props.get("children"))

    class MyComposite(Component):
        def render(self) -> object:
            return create_element(Lower, None, self.props.get("children"))

    c = Container()
    with act():
        create_root(c).render(create_element(MyComposite, None, "Interpolated String Child"))
    host = _host(c)
    assert host.tagName.upper() == "DIV"
    assert _element_children(host) == []
