# Translated from: packages/react-dom/src/__tests__/ReactDOMFiberAsync-test.js
# Burndown v179: createRoot flushSync batching, lifecycle guard, stale root commits.
from __future__ import annotations

from collections.abc import Iterator
from typing import Any, cast

import pytest
from ryact import Component, create_element, create_ref
from ryact.dev import is_dev, set_dev
from ryact_dom.dom import Container, ElementNode, SyntheticEvent
from ryact_dom.dom_internals import reset_component_dom_registry
from ryact_dom.error_reporting import console_error_log
from ryact_dom.legacy_mount import reset_legacy_mount_state
from ryact_dom.root import _dom_class_instance_cache_key, create_root
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


def _root(container: Container | None = None) -> tuple[Container, Any]:
    c = container or Container()
    c.console_error_log = []  # type: ignore[attr-defined]
    return c, create_root(c)


def _class_instance(root: Any, cls: type[Component]) -> Component:
    key = _dom_class_instance_cache_key(cls, None, ("host", ()), 0)
    return cast(Component, root._class_instances[key])


def test_flush_sync_batches_sync_updates_and_flushes_them_at_the_end_of_the_batch() -> None:
    c, root = _root()
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
    inst = _class_instance(root, Comp)

    with act():
        inst.push("A")
    assert ops == ["A"]
    assert c.text_content == "A"

    def batch() -> None:
        inst.push("B")
        inst.push("C")
        assert c.text_content == "A"
        assert ops == ["A"]

    with act():
        root.flush_sync(batch)
    assert c.text_content == "ABC"
    assert ops == ["A", "ABC"]

    with act():
        inst.push("D")
    assert c.text_content == "ABCD"
    assert ops == ["A", "ABC", "ABCD"]


def test_flush_sync_logs_an_error_if_already_performing_work() -> None:
    c, root = _root()

    class Comp(Component):
        def componentDidUpdate(self, *_a: object) -> None:  # noqa: N802
            root.flush_sync()

        def render(self) -> object:
            return None

    with act():
        root.render(create_element(Comp, {"tick": 0}))
    with act():
        root.flush_sync(lambda: root.render(create_element(Comp, {"tick": 1})))
    assert any("flushSync was called from inside a lifecycle method" in str(x) for x in console_error_log(c))


def test_unmounted_roots_should_never_clear_newer_root_content_from_a_container() -> None:
    c = Container()
    c.console_error_log = []  # type: ignore[attr-defined]
    btn_ref = create_ref()
    old_root_holder: dict[str, Any] = {}

    class OldApp(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self._state = {"value": "old"}

        def hide_on_click(self, _ev: SyntheticEvent) -> None:
            self.set_state({"value": "update"})
            cast(Any, old_root_holder["root"]).flush_sync(lambda: cast(Any, old_root_holder["root"]).unmount())

        def render(self) -> object:
            return create_element(
                "button",
                {"ref": btn_ref, "onClick": self.hide_on_click},
                str(self.state["value"]),
            )

    class NewApp(Component):
        def render(self) -> object:
            return create_element("span", None, "new")

    old_root = create_root(c)
    old_root_holder["root"] = old_root
    with act():
        old_root.render(create_element(OldApp))
    btn = cast(ElementNode, btn_ref.current)
    assert btn is not None
    btn.dispatch_event("click")
    assert c.text_content == ""

    new_root = create_root(c)
    with act():
        new_root.render(create_element(NewApp))
    btn.dispatch_event("click")
    assert c.text_content == "new"
