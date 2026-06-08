# Translated from: packages/react-dom/src/__tests__/ReactDOMFiberAsync-test.js
# Burndown v180: passive effects across roots and flushSync async-then-sync batching.
from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest
from ryact import Component, Fragment, create_element, use_effect, use_state
from ryact.dev import is_dev, set_dev
from ryact_dom.dom import Container
from ryact_dom.dom_internals import reset_component_dom_registry
from ryact_dom.legacy_mount import reset_legacy_mount_state
from ryact_dom.root import create_root, _dom_class_instance_cache_key
from ryact_dom.root_dev import reset_root_dev_state
from ryact_testkit import act, set_act_environment_enabled


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


def test_regression_test_does_not_drop_passive_effects_across_roots_17066() -> None:
    def App(**_props: object) -> object:
        step, set_step = use_state(0)

        def effect() -> None:
            if step < 3:
                set_step(step + 1)

        use_effect(effect, (step,))
        return create_element("span", None, "Finished" if step == 3 else "Unresolved")

    containers = [Container() for _ in range(3)]
    roots = [create_root(c) for c in containers]
    with act():
        for root in roots:
            root.render(create_element(App))
    for c in containers:
        assert c.text_content == "Finished"


def test_flush_sync_flushes_updates_before_end_of_the_tick() -> None:
    c = Container()
    root = create_root(c)
    ops: list[str] = []

    class Comp(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self._state = {"text": ""}

        def push(self, val: str) -> None:
            self.set_state(lambda state: {"text": str(state["text"]) + val})

        def componentDidUpdate(self, *_a: object) -> None:  # noqa: N802
            ops.append(str(self.state["text"]))

        def render(self) -> object:
            return create_element("span", None, str(self.state["text"]))

    with act():
        root.render(create_element(Comp))
    inst = root._class_instances[_dom_class_instance_cache_key(Comp, None, ("host", ()), 0)]
    rr = root._reconciler_root
    rr._is_batching_updates = True  # type: ignore[attr-defined]
    try:
        inst.push("A")
        assert c.text_content == ""
        assert ops == []

        def batch() -> None:
            inst.push("B")
            inst.push("C")
            assert c.text_content == ""
            assert ops == []

        with act():
            root.flush_sync(batch)
    finally:
        rr._is_batching_updates = False  # type: ignore[attr-defined]

    assert c.text_content == "ABC"
    assert ops == ["ABC"]

    def _flush_root() -> None:
        from ryact.reconciler import perform_work

        commit = rr._commit_fn
        if callable(commit):
            perform_work(rr, commit)

    with act():
        rr._is_batching_updates = True  # type: ignore[attr-defined]
        try:
            inst.push("D")
            assert c.text_content == "ABC"
            assert ops == ["ABC"]
        finally:
            rr._is_batching_updates = False  # type: ignore[attr-defined]
    with act(flush=_flush_root):
        pass
    assert c.text_content == "ABCD"
    assert ops == ["ABC", "ABCD"]
