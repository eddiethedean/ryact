# Translated from: packages/react-dom/src/__tests__/ReactUpdates-test.js
# Burndown v167: createRoot update depth guards, hidden subtrees, batch limits.
from __future__ import annotations

from collections.abc import Iterator
from typing import Any, cast

import pytest
from ryact import Component, create_element, create_ref, use_effect, use_layout_effect, use_state
from ryact.dev import is_dev, set_dev
from ryact_dom.dom import Container
from ryact_dom.dom_internals import reset_component_dom_registry
from ryact_dom.legacy_mount import batched_updates, reset_legacy_mount_state
from ryact_dom.root import create_root
from ryact_dom.root_dev import reset_root_dev_state
from ryact_testkit import WarningCapture

_update_limit = 55


@pytest.fixture(autouse=True)
def _dev_and_reset() -> Iterator[None]:
    global _update_limit
    prev = is_dev()
    set_dev(True)
    _update_limit = 55
    reset_legacy_mount_state()
    reset_root_dev_state()
    reset_component_dom_registry()
    yield
    _update_limit = 55
    reset_legacy_mount_state()
    reset_root_dev_state()
    reset_component_dom_registry()
    set_dev(prev)


def _root(container: Container | None = None) -> tuple[Container, Any]:
    c = container or Container()
    c.console_error_log = []  # type: ignore[attr-defined]
    c.window_error_log = []  # type: ignore[attr-defined]
    return c, create_root(c)


def test_synchronously_renders_hidden_subtrees() -> None:
    ops: list[str] = []

    class Baz(Component):
        def render(self) -> object:
            ops.append("Baz")
            return None

    class Bar(Component):
        def render(self) -> object:
            ops.append("Bar")
            return None

    class Foo(Component):
        def render(self) -> object:
            ops.append("Foo")
            return create_element(
                "div",
                None,
                create_element("div", {"hidden": True}, create_element(Bar)),
                create_element(Baz),
            )

    c, root = _root()
    root.render(create_element(Foo))
    assert ops == ["Foo", "Bar", "Baz"]
    ops.clear()
    root.render(create_element(Foo))
    assert ops == ["Foo", "Bar", "Baz"]


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

    c, root = _root()
    with WarningCapture() as cap:
        root.render(create_element(Foo))
    assert any("Cannot update during an existing state transition" in str(r.message) for r in cap.records)
    assert ops[:2] == ["base: 0, memoized: 0", "base: 1, memoized: 1"]


def test_does_not_fall_into_an_infinite_update_loop() -> None:
    class NonTerminating(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self._state = {"step": 0}

        def componentDidMount(self) -> None:  # noqa: N802
            self.set_state({"step": 1})

        def componentDidUpdate(self, *_args: object) -> None:  # noqa: N802
            self.set_state({"step": 2})

        def render(self) -> object:
            return create_element(
                "div",
                None,
                f"Hello {self.props.get('name')} {self.state['step']}",
            )

    c, root = _root()
    with pytest.raises(RuntimeError, match="Maximum update depth exceeded"):
        root.render(create_element(NonTerminating, {"name": "x"}))


def test_does_not_fall_into_an_infinite_update_loop_with_uselayouteffect() -> None:
    def App() -> object:
        step, set_step = use_state(0)

        def effect() -> None:
            set_step(lambda x: x + 1)

        use_layout_effect(effect)
        return create_element("span", None, str(step))

    c, root = _root()
    with pytest.raises(RuntimeError, match="Maximum"):
        root.render(create_element(App))


def test_can_recover_after_falling_into_an_infinite_update_loop() -> None:
    class NonTerminating(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self._state = {"step": 0}

        def componentDidMount(self) -> None:  # noqa: N802
            self.set_state({"step": 1})

        def componentDidUpdate(self, *_args: object) -> None:  # noqa: N802
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

    c, root = _root()
    with pytest.raises(RuntimeError, match="Maximum"):
        root.render(create_element(NonTerminating))
    root.render(create_element(Terminating))
    assert c.text_content == "1"
    with pytest.raises(RuntimeError, match="Maximum"):
        root.render(create_element(NonTerminating))
    root.render(create_element(Terminating))
    assert c.text_content == "1"


def test_does_not_fall_into_mutually_recursive_infinite_update_loop_with_same_container() -> None:
    c, root = _root()

    class A(Component):
        def componentDidMount(self) -> None:  # noqa: N802
            root.render(create_element(B))

        def render(self) -> object:
            return None

    class B(Component):
        def componentDidMount(self) -> None:  # noqa: N802
            root.render(create_element(A))

        def render(self) -> object:
            return None

    with pytest.raises(RuntimeError, match="Maximum"):
        root.render(create_element(A))


def test_does_not_fall_into_an_infinite_error_loop() -> None:
    def BadRender(**_props: object) -> object:
        raise RuntimeError("error")

    class ErrorBoundary(Component):
        def componentDidCatch(self, _err: BaseException) -> None:  # noqa: N802
            self.set_state({})
            cast(Component, self.props.get("parent")).remount()

        def render(self) -> object:
            return create_element(BadRender)

    class NonTerminating(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self._state = {"step": 0}

        def remount(self) -> None:
            self.set_state(lambda state: {"step": int(state["step"]) + 1})

        def render(self) -> object:
            return create_element(ErrorBoundary, {"key": self.state["step"], "parent": self})

    c, root = _root()
    with pytest.raises(RuntimeError, match="Maximum"):
        root.render(create_element(NonTerminating))


def test_can_render_ridiculously_large_number_of_roots_without_triggering_infinite_update_loop_error() -> None:
    ops: list[str] = []

    def Triggerable(**props: object) -> object:
        trigger = props.get("trigger")
        step, set_step = use_state(0)

        def effect() -> None:
            if trigger:
                ops.append("Trigger")
                set_step(lambda c: c + 1)

        use_effect(effect, [trigger])
        return create_element("div", None, str(step))

    class Foo(Component):
        def componentDidMount(self) -> None:  # noqa: N802
            limit = 200
            for i in range(limit):
                child = Container()
                if i < limit - 1:
                    create_root(child).render(create_element(Triggerable))
                else:
                    create_root(child).render(create_element(Triggerable, {"trigger": True}))

        def render(self) -> object:
            return None

    c, root = _root()
    root.render(create_element(Foo))
    assert ops == ["Trigger"]


def test_resets_the_update_counter_for_unrelated_updates() -> None:
    global _update_limit

    class EventuallyTerminating(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self._state = {"step": 0}

        def componentDidMount(self) -> None:  # noqa: N802
            self.set_state({"step": 1})

        def componentDidUpdate(self, *_args: object) -> None:  # noqa: N802
            if self.state["step"] < _update_limit:
                self.set_state({"step": self.state["step"] + 1})

        def render(self) -> object:
            return create_element("span", None, str(self.state["step"]))

    c, root = _root()
    ref = create_ref()
    _update_limit = 55
    with pytest.raises(RuntimeError, match="Maximum"):
        root.render(create_element(EventuallyTerminating, {"ref": ref}))

    _update_limit = 45
    root.render(create_element(EventuallyTerminating, {"ref": ref}))
    assert c.text_content == "45"
    inst = cast(Component, ref.current)
    inst.set_state({"step": 0})
    assert c.text_content == "45"
    inst.set_state({"step": 0})
    assert c.text_content == "45"


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

    c, root = _root()
    root.render(create_element(App))
    assert len(subscribers) == 1

    def batch() -> None:
        for _ in range(1200):
            subscribers[0].set_state({"value": "update"})

    batched_updates(batch)
    assert c.text_content == "update"
