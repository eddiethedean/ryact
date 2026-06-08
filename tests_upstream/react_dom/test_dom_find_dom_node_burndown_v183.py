# Translated from: packages/react-dom/src/__tests__/findDOMNodeFB-test.js
# Burndown v183: findDOMNode validation, unmount, and StrictMode warnings.
from __future__ import annotations

from collections.abc import Iterator
from typing import Any, cast

import pytest
from ryact import Component, StrictMode, create_element, create_ref
from ryact.dev import is_dev, set_dev
from ryact_dom.dom import Container, ElementNode
from ryact_dom.dom_internals import find_dom_node, reset_component_dom_registry
from ryact_dom.legacy_mount import legacy_render, reset_legacy_mount_state, unmount_component_at_node
from ryact_testkit import WarningCapture


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


def test_find_dom_node_should_return_null_if_passed_null() -> None:
    assert find_dom_node(None) is None


def test_find_dom_node_should_find_dom_element() -> None:
    class MyNode(Component):
        def render(self) -> object:
            return create_element("div", None, "Noise")

    c = Container()
    inst = legacy_render(create_element(MyNode), c)
    my_div = find_dom_node(inst)
    assert isinstance(my_div, ElementNode)
    assert my_div.tag.lower() == "div"
    assert find_dom_node(my_div) is my_div


def test_find_dom_node_should_find_dom_element_after_an_update_from_null() -> None:
    class Bar(Component):
        def render(self) -> object:
            if self.props.get("flag"):
                return create_element("span", None, "A")
            return None

    class MyNode(Component):
        def render(self) -> object:
            return create_element(Bar, {"flag": self.props.get("flag")})

    c = Container()
    inst_a = legacy_render(create_element(MyNode, {"flag": False}), c)
    assert find_dom_node(inst_a) is None
    inst_b = legacy_render(create_element(MyNode, {"flag": True}), c)
    assert inst_a is inst_b
    node = find_dom_node(inst_b)
    assert isinstance(node, ElementNode)
    assert node.tag.lower() == "span"


def test_find_dom_node_should_reject_random_objects() -> None:
    with pytest.raises(TypeError, match="Argument appears to not be a ReactComponent. Keys: foo"):
        find_dom_node({"foo": "bar"})


def test_find_dom_node_should_reject_unmounted_objects_with_render_func() -> None:
    class Foo(Component):
        def render(self) -> object:
            return create_element("div")

    c = Container()
    inst = legacy_render(create_element(Foo), c)
    unmount_component_at_node(c)
    with pytest.raises(RuntimeError, match="Unable to find node on an unmounted component."):
        find_dom_node(inst)


def test_find_dom_node_should_not_throw_when_called_within_a_component_that_is_not_mounted() -> None:
    class Bar(Component):
        def componentWillMount(self) -> None:  # noqa: N802
            assert find_dom_node(self) is None

        def render(self) -> object:
            return create_element("div")

    c = Container()
    legacy_render(create_element(Bar), c)


def test_find_dom_node_should_warn_if_used_to_find_a_host_component_inside_strict_mode() -> None:
    child_ref = create_ref()

    class ContainsStrictModeChild(Component):
        def render(self) -> object:
            return create_element(
                "div",
                None,
                create_element(StrictMode, None, create_element("div", {"ref": child_ref})),
            )

    c = Container()
    parent = legacy_render(create_element(ContainsStrictModeChild), c)
    with WarningCapture() as cap:
        match = find_dom_node(parent)
    assert match is find_dom_node(cast(Any, child_ref.current))
    assert any("renders StrictMode children" in w for w in cap.messages)


def test_find_dom_node_should_warn_if_passed_a_component_that_is_inside_strict_mode() -> None:
    child_ref = create_ref()

    class IsInStrictMode(Component):
        def render(self) -> object:
            return create_element("div", {"ref": child_ref})

    c = Container()
    parent_box: dict[str, Any] = {}
    legacy_render(
        create_element(
            StrictMode,
            None,
            create_element(IsInStrictMode, {"ref": lambda inst: parent_box.setdefault("inst", inst)}),
        ),
        c,
    )
    parent = cast(Component, parent_box["inst"])
    with WarningCapture() as cap:
        match = find_dom_node(parent)
    assert match is find_dom_node(cast(Any, child_ref.current))
    assert any("is inside StrictMode" in w for w in cap.messages)
