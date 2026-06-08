# Translated from: packages/react-dom/src/__tests__/ReactMountDestruction-test.js
# Burndown v178: createRoot destruction and legacy unmount warnings on host nodes.
from __future__ import annotations

from collections.abc import Iterator
from typing import Any, cast

import pytest
from ryact import create_element
from ryact.dev import is_dev, set_dev
from ryact_dom.dom import Container, ElementNode
from ryact_dom.dom_internals import reset_component_dom_registry
from ryact_dom.legacy_mount import legacy_render, reset_legacy_mount_state, unmount_component_at_node
from ryact_dom.root import create_root
from ryact_dom.root_dev import reset_root_dev_state
from ryact_testkit import WarningCapture, act, set_act_environment_enabled


@pytest.fixture(autouse=True)
def _dev_and_reset() -> Iterator[None]:
    prev = is_dev()
    set_dev(True)
    reset_legacy_mount_state()
    reset_root_dev_state()
    reset_component_dom_registry()
    set_act_environment_enabled(True)
    yield
    reset_legacy_mount_state()
    reset_root_dev_state()
    reset_component_dom_registry()
    set_act_environment_enabled(False)
    set_dev(prev)


def _host_class(c: Container) -> str:
    host = c.root.children[0]
    assert isinstance(host, ElementNode)
    return str(host.props.get("className", host.props.get("class", "")))


def test_should_destroy_a_react_root_upon_request() -> None:
    c1 = Container()
    c2 = Container()
    root1 = create_root(c1)
    root2 = create_root(c2)
    with act():
        root1.render(create_element("div", {"className": "firstReactDiv"}))
        root2.render(create_element("div", {"className": "secondReactDiv"}))
    assert _host_class(c1) == "firstReactDiv"
    assert _host_class(c2) == "secondReactDiv"
    with act():
        root1.unmount()
    assert c1.text_content == ""
    with act():
        root2.unmount()
    assert c2.text_content == ""


def test_should_warn_when_unmounting_a_non_container_root_node() -> None:
    c = Container()
    legacy_render(
        create_element(
            "div",
            None,
            create_element("div", None, create_element("span", None, "hello")),
        ),
        c,
    )
    root_host = cast(ElementNode, c.root.children[0])
    with WarningCapture() as cap:
        unmount_component_at_node(root_host)
    assert any(
        "may have accidentally passed in a React root node instead of its container" in str(r.message)
        for r in cap.records
    )


def test_should_warn_when_unmounting_a_non_container_non_root_node() -> None:
    c = Container()
    legacy_render(
        create_element(
            "div",
            None,
            create_element(
                "div",
                None,
                create_element("span", None, "hello"),
                create_element("span", None, "world"),
            ),
        ),
        c,
    )
    outer = cast(ElementNode, c.root.children[0])
    inner = cast(ElementNode, outer.children[0])
    with WarningCapture() as cap:
        unmount_component_at_node(inner)
    assert any(
        "have the parent component update its state and rerender" in str(r.message)
        for r in cap.records
    )
    assert not any(
        "may have accidentally passed in a React root node instead of its container" in str(r.message)
        for r in cap.records
    )
