# Translated from: packages/react-dom/src/__tests__/ReactLegacyUpdates-test.js
# Burndown v166: layout-effect loop guard, error-loop guard, multi-root depth reset.
from __future__ import annotations

from collections.abc import Iterator
from typing import Any, cast

import pytest
from ryact import Component, create_element, create_portal, create_ref, use_layout_effect, use_state
from ryact.dev import is_dev, set_dev
from ryact_dom.dom import Container
from ryact_dom.dom_internals import find_dom_node, reset_component_dom_registry
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


def test_does_not_fall_into_an_infinite_update_loop_with_uselayouteffect() -> None:
    def App() -> object:
        step, set_step = use_state(0)

        def effect() -> None:
            set_step(lambda x: x + 1)

        use_layout_effect(effect)
        return create_element("span", None, str(step))

    with pytest.raises(RuntimeError, match="Maximum"):
        legacy_render(create_element(App), Container())


def test_does_not_fall_into_an_infinite_error_loop() -> None:
    def BadRender(**_props: object) -> object:
        raise RuntimeError("error")

    class ErrorBoundary(Component):
        def componentDidCatch(self, _err: BaseException) -> None:  # noqa: N802
            self.set_state({})
            cast(Any, self.props.get("parent")).remount()

        def render(self) -> object:
            return create_element(BadRender)

    class NonTerminating(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self._state = {"step": 0}

        def remount(self) -> None:
            self.set_state(lambda state: {"step": int(state["step"]) + 1})

        def render(self) -> object:
            return create_element(ErrorBoundary, {"parent": self})

    with pytest.raises(RuntimeError, match="Maximum"):
        legacy_render(create_element(NonTerminating), Container())


def test_can_render_ridiculously_large_number_of_roots_without_triggering_infinite_update_loop_error() -> None:
    class Foo(Component):
        def componentDidMount(self) -> None:  # noqa: N802
            limit = 200
            for i in range(limit):
                child = Container()
                if i < limit - 1:
                    legacy_render(create_element("span", None, str(i)), child)
                else:

                    def done() -> None:
                        self.set_state({})

                    legacy_render(create_element("span", None, "last"), child, callback=done)

        def render(self) -> object:
            return None

    legacy_render(create_element(Foo), Container())


@pytest.mark.skip(reason="Implemented in test_dom_legacy_updates_burndown_v177.py")
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


@pytest.mark.skip(reason="Implemented in test_dom_legacy_updates_burndown_v177.py")
def test_should_queue_mount_ready_handlers_across_different_roots() -> None:
    b_container = Container()
    a_updated = False
    b_inst_box: dict[str, Any] = {}

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
            assert find_dom_node(b_inst_box["inst"]).text_content == "B1"
            a_updated = True

        def render(self) -> object:
            return create_element(
                "div",
                None,
                create_element("span", None, f"A{self.state['x']}"),
                create_portal(
                    children=create_element(B, {"ref": lambda inst: b_inst_box.setdefault("inst", inst)}),
                    container=b_container,
                ),
            )

    a_container = Container()
    a = legacy_render(create_element(A), a_container)

    def batch() -> None:
        a.set_state({"x": 1})
        cast(Component, b_inst_box["inst"]).set_state({"x": 1})

    batched_updates(batch)
    assert a_updated is True
