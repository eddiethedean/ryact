# Translated from: packages/react-dom/src/__tests__/ReactLegacyUpdates-test.js
# Burndown v157: hidden subtrees, nested update depth guard.
from __future__ import annotations

from collections.abc import Iterator

import pytest
from ryact import Component, create_element, create_ref
from ryact.dev import is_dev, set_dev
from ryact_dom.dom import Container
from ryact_dom.dom_internals import reset_component_dom_registry
from ryact_dom.legacy_mount import legacy_render, reset_legacy_mount_state, unmount_component_at_node

_update_limit = 55


@pytest.fixture(autouse=True)
def _dev_and_legacy_state() -> Iterator[None]:
    prev = is_dev()
    set_dev(True)
    reset_legacy_mount_state()
    reset_component_dom_registry()
    yield
    reset_legacy_mount_state()
    reset_component_dom_registry()


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

    c = Container()
    legacy_render(create_element(Foo), c)
    assert ops == ["Foo", "Bar", "Baz"]
    ops.clear()
    legacy_render(create_element(Foo), c)
    assert ops == ["Foo", "Bar", "Baz"]


def test_does_not_fall_into_an_infinite_update_loop() -> None:
    class NonTerminating(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self._state = {"step": 0}

        def componentDidMount(self) -> None:  # noqa: N802
            self.set_state({"step": 1})

        def UNSAFE_componentWillUpdate(self, _np: object, _ns: object) -> None:  # noqa: N802
            self.set_state({"step": 2})

        def render(self) -> object:
            return create_element("div", None, f"Hello {self.props.get('name')} {self.state['step']}")

    c = Container()
    with pytest.raises(RuntimeError, match="Maximum update depth exceeded"):
        legacy_render(create_element(NonTerminating, {"name": "x"}), c)


def test_resets_the_update_counter_for_unrelated_updates() -> None:
    global _update_limit

    class EventuallyTerminating(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self._state = {"step": 0}

        def componentDidMount(self) -> None:  # noqa: N802
            self.set_state({"step": 1})

        def componentDidUpdate(self, *_a: object) -> None:  # noqa: N802
            if self.state["step"] < _update_limit:
                self.set_state({"step": self.state["step"] + 1})

        def render(self) -> object:
            return create_element("span", None, str(self.state["step"]))

    c = Container()
    ref = create_ref()
    _update_limit = 55
    with pytest.raises(RuntimeError, match="Maximum update depth exceeded"):
        legacy_render(create_element(EventuallyTerminating, {"ref": ref}), c)

    _update_limit = 45
    unmount_component_at_node(c)
    legacy_render(create_element(EventuallyTerminating, {"ref": ref}), c)
    assert c.text_content == "45"
    inst = ref.current
    assert inst is not None
    inst.set_state({"step": 0})
    assert c.text_content == "45"
    inst.set_state({"step": 0})
    assert c.text_content == "45"
