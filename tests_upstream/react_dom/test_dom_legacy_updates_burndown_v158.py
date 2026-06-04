# Translated from: packages/react-dom/src/__tests__/ReactLegacyUpdates-test.js
# Burndown v158: render-phase base state, mutual legacy_render guard, recover, batch depth.
from __future__ import annotations

from collections.abc import Iterator

import pytest
from ryact import Component, create_element
from ryact.dev import is_dev, set_dev
from ryact_dom.dom import Container
from ryact_dom.dom_internals import reset_component_dom_registry
from ryact_dom.legacy_mount import (
    batched_updates,
    legacy_render,
    reset_legacy_mount_state,
)
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


def test_uses_correct_base_state_for_setstate_inside_render_phase() -> None:
    ops: list[str] = []

    class Foo(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self._state = {"step": 0}

        def render(self) -> object:
            memoized_step = self.state["step"]

            def updater(base: dict[str, int], _props: object | None = None) -> dict[str, int] | None:
                base_step = base["step"]
                ops.append(f"base: {base_step}, memoized: {memoized_step}")
                return {"step": 1} if base_step == 0 else None

            self.set_state(updater)
            return None

    c = Container()
    with WarningCapture() as cap:
        legacy_render(create_element(Foo), c)
    assert any("Cannot update during an existing state transition" in str(r.message) for r in cap.records)
    assert ops[:2] == ["base: 0, memoized: 0", "base: 1, memoized: 1"]


def test_does_not_fall_into_mutually_recursive_infinite_update_loop_with_same_container() -> None:
    c = Container()

    class A(Component):
        def componentDidMount(self) -> None:  # noqa: N802
            legacy_render(create_element(B), c)

        def render(self) -> object:
            return None

    class B(Component):
        def componentDidMount(self) -> None:  # noqa: N802
            legacy_render(create_element(A), c)

        def render(self) -> object:
            return None

    with pytest.raises(RuntimeError, match="Maximum update depth exceeded"):
        legacy_render(create_element(A), c)


def test_can_recover_after_falling_into_an_infinite_update_loop() -> None:
    class NonTerminating(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self._state = {"step": 0}

        def componentDidMount(self) -> None:  # noqa: N802
            self.set_state({"step": 1})

        def UNSAFE_componentWillUpdate(self, _np: object, _ns: object) -> None:  # noqa: N802
            self.set_state({"step": 2})

        def render(self) -> object:
            return create_element("span", None, str(self.state["step"]))

    class Terminating(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self._state = {"step": 0}

        def componentDidMount(self) -> None:  # noqa: N802
            self.set_state({"step": 1})

        def render(self) -> object:
            return create_element("span", None, str(self.state["step"]))

    c = Container()
    with pytest.raises(RuntimeError, match="Maximum update depth exceeded"):
        legacy_render(create_element(NonTerminating), c)

    legacy_render(create_element(Terminating), c)
    assert c.text_content == "1"

    with pytest.raises(RuntimeError, match="Maximum update depth exceeded"):
        legacy_render(create_element(NonTerminating), c)

    legacy_render(create_element(Terminating), c)
    assert c.text_content == "1"


def test_can_schedule_ridiculously_many_updates_within_the_same_batch_without_triggering_a_maximum_update_error() -> (
    None
):
    subscribers: list[Component] = []

    class App(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self._state = {"value": "initial"}

        def componentDidMount(self) -> None:  # noqa: N802
            subscribers.append(self)

        def render(self) -> object:
            return create_element("span", None, str(self.state["value"]))

    c = Container()
    legacy_render(create_element(App), c)
    assert len(subscribers) == 1

    def batch() -> None:
        for _ in range(1200):
            subscribers[0].set_state({"value": "update"})

    batched_updates(batch)
    assert c.text_content == "update"
