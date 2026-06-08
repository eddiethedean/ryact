# Translated from: packages/react-dom/src/__tests__/ReactLegacyErrorBoundaries-test.internal.js
# Burndown v171: unmount lifecycle catch, refs on abort, removals, first commit error.
from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest
from ryact import Component, Fragment, create_element, create_ref
from ryact.dev import is_dev, set_dev
from ryact_dom.dom import Container, ElementNode
from ryact_dom.dom_internals import reset_component_dom_registry
from ryact_dom.legacy_mount import legacy_render, reset_legacy_mount_state


@pytest.fixture(autouse=True)
def _dev_and_legacy() -> Iterator[None]:
    prev = is_dev()
    set_dev(True)
    reset_legacy_mount_state()
    reset_component_dom_registry()
    yield
    reset_legacy_mount_state()
    reset_component_dom_registry()
    set_dev(prev)


def _text(c: Container) -> str:
    return c.text_content


class BrokenRender(Component):
    def render(self) -> object:
        raise RuntimeError("Hello")


class BrokenComponentDidMount(Component):
    def componentDidMount(self) -> None:  # noqa: N802
        raise RuntimeError(str(self.props.get("msg", "Hello")))

    def render(self) -> object:
        return create_element("span", None, "x")


class BrokenComponentWillUnmount(Component):
    def componentWillUnmount(self) -> None:  # noqa: N802
        raise RuntimeError("Hello")

    def render(self) -> object:
        return create_element("span", None, "x")


class ErrorBoundary(Component):
    def __init__(self, **props: object) -> None:
        super().__init__(**props)
        self._state: dict[str, Any] = {"error": None}
        self._did_catch_errors: list[str] = []

    def componentDidCatch(self, error: BaseException) -> None:  # noqa: N802
        self._did_catch_errors.append(str(error))
        self.set_state({"error": error})

    def render(self) -> object:
        err = self.state.get("error")
        if err is not None and not self.props.get("forceRetry"):
            ref = self.props.get("errorMessageRef")
            return create_element("span", {"ref": ref}, f"Caught an error: {err}.")
        children = self.props.get("children")
        if isinstance(children, tuple):
            return create_element(Fragment, None, *children)
        return children


def test_recovers_from_componentwillunmount_errors_on_update() -> None:
    c = Container()
    legacy_render(
        create_element(
            ErrorBoundary,
            {"key": "eb"},
            create_element(BrokenComponentWillUnmount, {"key": "broken"}),
        ),
        c,
    )
    legacy_render(create_element(ErrorBoundary, {"key": "eb"}), c)
    assert _text(c) == "Caught an error: Hello."


def test_recovers_from_nested_componentwillunmount_errors_on_update() -> None:
    c = Container()
    legacy_render(
        create_element(
            ErrorBoundary,
            {"key": "outer", "name": "Outer"},
            create_element(
                ErrorBoundary,
                {"key": "inner", "name": "Inner"},
                create_element(BrokenComponentWillUnmount, {"key": "broken"}),
            ),
        ),
        c,
    )
    legacy_render(
        create_element(
            ErrorBoundary,
            {"key": "outer", "name": "Outer"},
            create_element(ErrorBoundary, {"key": "inner", "name": "Inner"}),
        ),
        c,
    )
    assert _text(c) == "Caught an error: Hello."


def test_doesnt_get_into_inconsistent_state_during_removals() -> None:
    c = Container()
    legacy_render(
        create_element(
            ErrorBoundary,
            {"key": "eb"},
            create_element("span", {"key": "n"}, "ok"),
            create_element(BrokenComponentWillUnmount, {"key": "broken"}),
        ),
        c,
    )
    legacy_render(create_element(ErrorBoundary, {"key": "eb"}), c)
    assert _text(c) == "Caught an error: Hello."


def test_keeps_refs_up_to_date_during_updates() -> None:
    ops: list[ElementNode | None] = []

    def child_ref(node: ElementNode | None) -> None:
        ops.append(node)

    c = Container()
    legacy_render(
        create_element(ErrorBoundary, {"key": "eb"}, create_element("div", {"key": "d", "ref": child_ref})),
        c,
    )
    assert len(ops) == 1
    assert isinstance(ops[0], ElementNode)

    legacy_render(
        create_element(
            ErrorBoundary,
            {"key": "eb"},
            create_element("div", {"key": "d", "ref": child_ref}),
            create_element(BrokenRender, {"key": "broken"}),
        ),
        c,
    )
    assert ops[-2:] == [ops[0], None]
    assert _text(c) == "Caught an error: Hello."


def test_resets_object_refs_if_mounting_aborts() -> None:
    child_ref = create_ref()
    error_ref = create_ref()
    c = Container()
    legacy_render(
        create_element(
            ErrorBoundary,
            {"key": "eb", "errorMessageRef": error_ref},
            create_element("div", {"key": "d", "ref": child_ref}),
            create_element(BrokenRender, {"key": "broken"}),
        ),
        c,
    )
    assert child_ref.current is None
    assert isinstance(error_ref.current, ElementNode)
    assert _text(c) == "Caught an error: Hello."


def test_resets_callback_refs_if_mounting_aborts() -> None:
    ops: list[tuple[str, ElementNode | None]] = []

    def child_ref(node: ElementNode | None) -> None:
        ops.append(("child", node))

    error_ref = create_ref()
    c = Container()
    legacy_render(
        create_element(
            ErrorBoundary,
            {"key": "eb", "errorMessageRef": error_ref},
            create_element("div", {"key": "d", "ref": child_ref}),
            create_element(BrokenRender, {"key": "broken"}),
        ),
        c,
    )
    assert ops == []
    assert isinstance(error_ref.current, ElementNode)
    assert _text(c) == "Caught an error: Hello."


def test_picks_the_right_boundary_when_handling_unmounting_errors() -> None:
    c = Container()
    legacy_render(
        create_element(
            ErrorBoundary,
            {"key": "outer", "name": "Outer"},
            create_element(
                ErrorBoundary,
                {"key": "inner", "name": "Inner"},
                create_element(BrokenComponentWillUnmount, {"key": "broken"}),
            ),
        ),
        c,
    )
    legacy_render(
        create_element(
            ErrorBoundary,
            {"key": "outer", "name": "Outer"},
            create_element(ErrorBoundary, {"key": "inner", "name": "Inner"}),
        ),
        c,
    )
    outer = c._ryact_dom_root._class_instances[(ErrorBoundary, "outer")]
    inner = c._ryact_dom_root._class_instances[(ErrorBoundary, "inner")]
    assert outer.state.get("error") is None
    assert inner.state.get("error") is not None
    assert _text(c) == "Caught an error: Hello."


def test_passes_first_error_when_two_errors_happen_in_commit() -> None:
    c = Container()
    legacy_render(
        create_element(
            ErrorBoundary,
            {"key": "eb"},
            create_element(BrokenComponentDidMount, {"key": "a", "msg": "A"}),
            create_element(BrokenComponentDidMount, {"key": "b", "msg": "B"}),
        ),
        c,
    )
    inst = c._ryact_dom_root._class_instances[(ErrorBoundary, "eb")]
    assert inst._did_catch_errors == ["A", "B"]
    assert _text(c) == "Caught an error: A."
