# Translated from: packages/react-dom/src/__tests__/ReactLegacyUpdates-test.js
# Burndown v177: legacy flush ordering and portal mount-ready handlers.
from __future__ import annotations

from collections.abc import Iterator
from typing import cast

import pytest
from ryact import Component, create_element, create_portal, create_ref
from ryact.dev import is_dev, set_dev
from ryact_dom.dom import Container
from ryact_dom.dom_internals import reset_component_dom_registry
from ryact_dom.legacy_mount import batched_updates, legacy_render, reset_legacy_mount_state


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


def test_should_flush_updates_in_the_correct_order() -> None:
    updates: list[str] = []

    class Inner(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self._state = {"x": 0}

        def render(self) -> object:
            updates.append(f"Inner-render-{self.props.get('x')}-{self.state['x']}")
            return create_element("span", None, "i")

        def componentDidUpdate(self, *_args: object) -> None:  # noqa: N802
            updates.append(f"Inner-didUpdate-{self.props.get('x')}-{self.state['x']}")

    class Outer(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self._state = {"x": 0}
            self.inner_ref = create_ref()

        def render(self) -> object:
            updates.append(f"Outer-render-{self.state['x']}")
            return create_element(Inner, {"x": self.state["x"], "ref": self.inner_ref})

        def componentDidUpdate(self, *_args: object) -> None:  # noqa: N802
            x = self.state["x"]
            updates.append(f"Outer-didUpdate-{x}")
            updates.append(f"Inner-setState-{x}")

            def cb() -> None:
                updates.append(f"Inner-callback-{x}")

            cast(Component, self.inner_ref.current).set_state({"x": x}, callback=cb)

    c = Container()
    inst = legacy_render(create_element(Outer), c)
    updates.clear()
    updates.append("Outer-setState-1")

    def cb1() -> None:
        updates.append("Outer-callback-1")
        updates.append("Outer-setState-2")

        def cb2() -> None:
            updates.append("Outer-callback-2")

        inst.set_state({"x": 2}, callback=cb2)

    inst.set_state({"x": 1}, callback=cb1)
    assert "Outer-render-2" in updates


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
    legacy_render(create_element(A), a_container)
    a_inst = cast(
        Component,
        [i for i in a_container._ryact_dom_root._class_instances.values() if type(i).__name__ == "A"][0],
    )

    def batch() -> None:
        a_inst.set_state({"x": 1})
        cast(Component, b_ref.current).set_state({"x": 1})

    batched_updates(batch)
    assert a_updated is True
