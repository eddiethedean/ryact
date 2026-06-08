# Translated from:
# - packages/react-dom/src/__tests__/ReactDOMLegacyFiber-test.js
# - packages/react-dom/src/__tests__/ReactLegacyUpdates-test.js
# Burndown v156: portal events, nested fragment findDOMNode, memo host, flush order.
from __future__ import annotations

from collections.abc import Iterator
from typing import cast

import pytest
from ryact import Component, create_element, create_portal, create_ref, fragment, memo
from ryact.dev import is_dev, set_dev
from ryact_dom.dom import Container, ElementNode, SyntheticEvent
from ryact_dom.dom_internals import find_dom_node, reset_component_dom_registry
from ryact_dom.legacy_mount import legacy_render, reset_legacy_mount_state


@pytest.fixture(autouse=True)
def _dev_and_legacy_state() -> Iterator[None]:
    is_dev()
    set_dev(True)
    reset_legacy_mount_state()
    reset_component_dom_registry()
    yield
    reset_legacy_mount_state()
    reset_component_dom_registry()


# --- ReactDOMLegacyFiber ---


def test_finds_the_first_child_even_when_fragment_is_nested() -> None:
    class Frag(Component):
        def render(self) -> object:
            return fragment(
                fragment(None, create_element("div", None, "a")),
                create_element("span", None, "b"),
            )

    c = Container()
    inst_ref = create_ref()
    legacy_render(create_element(Frag, {"ref": inst_ref}), c)
    node = find_dom_node(cast(Component, inst_ref.current))
    assert isinstance(node, ElementNode)
    assert node.tag.lower() == "div"
    assert c.text_content == "ab"


def test_should_bubble_events_from_the_portal_to_the_parent() -> None:
    host = Container()
    portal_c = Container()
    ops: list[str] = []

    def parent_click(_e: SyntheticEvent) -> None:
        ops.append("parent clicked")

    def portal_click(_e: SyntheticEvent) -> None:
        ops.append("portal clicked")

    legacy_render(
        create_element(
            "div",
            {"onClick": parent_click},
            create_portal(
                children=create_element("div", {"onClick": portal_click}, "portal"),
                container=portal_c,
            ),
        ),
        host,
    )
    portal_host = portal_c.root.children[0]
    assert isinstance(portal_host, ElementNode)
    portal_host.dispatch_event("click")
    assert ops == ["portal clicked", "parent clicked"]


def test_listens_to_events_that_do_not_exist_in_the_portal_subtree() -> None:
    host = Container()
    portal_c = Container()
    clicks: list[int] = []
    host_ref = create_ref()

    legacy_render(
        create_element(
            "div",
            {
                "onClick": lambda _e: clicks.append(1),
                "ref": host_ref,
            },
            create_portal(
                children=create_element("span", None, "portal"),
                container=portal_c,
            ),
        ),
        host,
    )
    div = host_ref.current
    assert isinstance(div, ElementNode)
    div.dispatch_event("click")
    assert clicks == [1]


def test_should_not_diff_memoized_host_components() -> None:
    did_call_on_change = False

    class Child(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self._state: dict[str, int] = {}

        def render(self) -> object:
            return None

        def capture_update(self, _e: SyntheticEvent) -> None:
            self.set_state({})

    class Input(Component):
        def render(self) -> object:
            return create_element("input", {"onClick": self.props["onClick"]})

    MemoInput = memo(Input)

    class Parent(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self._child_ref = create_ref()

        def render(self) -> object:
            child = self._child_ref.current
            capture = child.capture_update if isinstance(child, Child) else None
            return create_element(
                "div",
                {"onClickCapture": capture} if capture is not None else None,
                create_element(MemoInput, {"onClick": self._handle_click}),
                create_element(Child, {"ref": self._child_ref}),
            )

        def _handle_click(self, _e: SyntheticEvent) -> None:
            nonlocal did_call_on_change
            did_call_on_change = True

    c = Container()
    legacy_render(create_element(Parent), c)
    div = c.root.children[0]
    assert isinstance(div, ElementNode)
    inp = div.children[0]
    assert isinstance(inp, ElementNode)
    inp.dispatch_event("click")
    assert did_call_on_change is True


# --- ReactLegacyUpdates ---
