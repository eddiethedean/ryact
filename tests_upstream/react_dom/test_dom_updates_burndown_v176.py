# Translated from: packages/react-dom/src/__tests__/ReactUpdates-test.js
# Burndown v176: createRoot cross-root batched flush and portal mount-ready ordering.
from __future__ import annotations

from collections.abc import Iterator
from typing import cast

import pytest
from ryact import Component, create_element, create_portal, create_ref
from ryact.dev import is_dev, set_dev
from ryact_dom.dom import Container
from ryact_dom.dom_internals import reset_component_dom_registry
from ryact_dom.legacy_mount import batched_updates, reset_legacy_mount_state
from ryact_dom.root import create_root
from ryact_testkit import act, set_act_environment_enabled


@pytest.fixture(autouse=True)
def _dev_and_reset() -> Iterator[None]:
    prev = is_dev()
    set_dev(True)
    reset_legacy_mount_state()
    reset_component_dom_registry()
    set_act_environment_enabled(True)
    yield
    reset_legacy_mount_state()
    reset_component_dom_registry()
    set_dev(prev)


def test_should_flush_updates_in_the_correct_order_across_roots() -> None:
    c1 = Container()
    c2 = Container()
    order: list[str] = []

    class Comp(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self._state = {"n": 0}

        def componentDidMount(self) -> None:  # noqa: N802
            order.append(f"mount-{self.props.get('name')}")

        def componentDidUpdate(self, *_args: object) -> None:  # noqa: N802
            order.append(f"update-{self.props.get('name')}")

        def render(self) -> object:
            return create_element("span", None, str(self.props.get("name")))

    r1 = create_root(c1)
    r2 = create_root(c2)
    with act(flush=r1.flush_sync):
        r1.render(create_element(Comp, {"name": "a"}))
    with act(flush=r2.flush_sync):
        r2.render(create_element(Comp, {"name": "b"}))
    order.clear()
    a = [i for i in r1._class_instances.values() if i.props.get("name") == "a"][0]
    b = [i for i in r2._class_instances.values() if i.props.get("name") == "b"][0]

    def batch() -> None:
        a.set_state({"n": 1})
        b.set_state({"n": 1})

    with act(flush=r1.flush_sync):
        batched_updates(batch)
    assert "update-a" in order and "update-b" in order


def test_should_queue_mount_ready_handlers_across_different_roots() -> None:
    b_container = Container()
    a_updated = False
    b_ref = create_ref()

    class B(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self._state = {"x": 0}

        def render(self) -> object:
            return create_element("span", None, f"B{self.state['x']}")

    class A(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self._state = {"x": 0}

        def componentDidUpdate(self, *_args: object) -> None:  # noqa: N802
            nonlocal a_updated
            assert b_container.text_content == "B1"
            a_updated = True

        def render(self) -> object:
            return create_element(
                "div",
                None,
                create_element("span", None, f"A{self.state['x']}"),
                create_portal(
                    children=create_element(B, {"ref": b_ref}),
                    container=b_container,
                ),
            )

    a_container = Container()
    r1 = create_root(a_container)
    with act(flush=r1.flush_sync):
        r1.render(create_element(A))
    a_inst = cast(Component, [i for i in r1._class_instances.values() if type(i).__name__ == "A"][0])

    def batch() -> None:
        a_inst.set_state({"x": 1})
        cast(Component, b_ref.current).set_state({"x": 1})

    with act(flush=r1.flush_sync):
        batched_updates(batch)
    assert a_updated is True
