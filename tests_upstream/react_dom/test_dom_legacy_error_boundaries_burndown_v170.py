# Translated from: packages/react-dom/src/__tests__/ReactLegacyErrorBoundaries-test.internal.js
# Burndown v170: nested boundary propagation, lifecycle catch, reorders, bad root.
from __future__ import annotations

import random
from collections.abc import Iterator
from typing import Any

import pytest
from ryact import Component, Fragment, create_element
from ryact.dev import is_dev, set_dev
from ryact_dom.dom import Container
from ryact_dom.dom_internals import reset_component_dom_registry
from ryact_dom.legacy_mount import batched_updates, legacy_render, reset_legacy_mount_state


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
        raise RuntimeError("Hello")

    def render(self) -> object:
        return create_element("span", None, "x")


class BrokenComponentDidUpdate(Component):
    def render(self) -> object:
        return create_element("span", None, "x")

    def componentDidUpdate(self, *_args: object) -> None:  # noqa: N802
        raise RuntimeError("Hello")


class BrokenComponentWillMountErrorBoundary(Component):
    def UNSAFE_componentWillMount(self) -> None:  # noqa: N802
        raise RuntimeError("Hello")

    def componentDidCatch(self, _error: BaseException) -> None:  # noqa: N802
        pass

    def render(self) -> object:
        return create_element(BrokenRender, {"key": "broken"})


class BrokenRenderErrorBoundary(Component):
    def __init__(self, **props: object) -> None:
        super().__init__(**props)
        self._state: dict[str, Any] = {"error": None}

    def componentDidCatch(self, error: BaseException) -> None:  # noqa: N802
        self.set_state({"error": error})

    def render(self) -> object:
        if self.state.get("error") is not None:
            raise RuntimeError("Hello")
        return create_element(BrokenRender, {"key": "broken"})


class BrokenComponentDidMountErrorBoundary(Component):
    def componentDidMount(self) -> None:  # noqa: N802
        raise RuntimeError("Hello")

    def componentDidCatch(self, _error: BaseException) -> None:  # noqa: N802
        pass

    def render(self) -> object:
        return create_element("span", None, "ok")


class RetryErrorBoundary(Component):
    def componentDidCatch(self, _error: BaseException) -> None:  # noqa: N802
        self.set_state({})

    def render(self) -> object:
        return None


class ErrorBoundary(Component):
    def __init__(self, **props: object) -> None:
        super().__init__(**props)
        self._state: dict[str, Any] = {"error": None}

    def componentDidCatch(self, error: BaseException) -> None:  # noqa: N802
        self.set_state({"error": error})

    def render(self) -> object:
        err = self.state.get("error")
        if err is not None and not self.props.get("forceRetry"):
            return create_element("span", None, f"Caught an error: {err}.")
        children = self.props.get("children")
        if isinstance(children, tuple):
            return create_element(Fragment, None, *children)
        return children


class Normal(Component):
    def render(self) -> object:
        return create_element("span", None, "N")


_fail_reorder_render = False


class MaybeBrokenRender(Component):
    def render(self) -> object:
        if _fail_reorder_render:
            raise RuntimeError("Hello")
        return create_element("div", None, self.props.get("children"))


def _shuffled_error_boundary_children() -> tuple[object, ...]:
    elements: list[object] = [create_element(Normal, {"key": str(i)}) for i in range(20)]
    elements.append(create_element(MaybeBrokenRender, {"key": "broken"}))
    random.shuffle(elements)
    return tuple(elements)


def test_propagates_errors_on_retry_on_mounting() -> None:
    c = Container()
    legacy_render(
        create_element(
            ErrorBoundary,
            {"key": "eb"},
            create_element(RetryErrorBoundary, {"key": "retry"}),
            create_element(BrokenRender, {"key": "broken"}),
        ),
        c,
    )
    assert _text(c) == "Caught an error: Hello."


def test_propagates_errors_inside_boundary_during_componentwillmount() -> None:
    c = Container()
    legacy_render(
        create_element(
            ErrorBoundary,
            {"key": "eb"},
            create_element(BrokenComponentWillMountErrorBoundary, {"key": "inner"}),
        ),
        c,
    )
    assert _text(c) == "Caught an error: Hello."


def test_propagates_errors_inside_boundary_while_rendering_error_state() -> None:
    c = Container()
    legacy_render(
        create_element(
            ErrorBoundary,
            {"key": "eb"},
            create_element(
                BrokenRenderErrorBoundary,
                {"key": "inner"},
                create_element(BrokenRender, {"key": "broken"}),
            ),
        ),
        c,
    )
    assert _text(c) == "Caught an error: Hello."


def test_propagates_errors_inside_boundary_during_componentdidmount() -> None:
    c = Container()
    legacy_render(
        create_element(
            ErrorBoundary,
            {"key": "eb"},
            create_element(BrokenComponentDidMountErrorBoundary, {"key": "inner"}),
        ),
        c,
    )
    assert _text(c) == "Caught an error: Hello."


def test_propagates_uncaught_error_inside_unbatched_initial_mount() -> None:
    class Foo(Component):
        def render(self) -> object:
            raise RuntimeError("foo error")

    c = Container()
    with pytest.raises(RuntimeError, match="foo error"):
        batched_updates(lambda: legacy_render(create_element(Foo), c))


def test_discards_a_bad_root_if_the_root_component_fails() -> None:
    c = Container()
    with pytest.raises(RuntimeError, match="Hello"):
        legacy_render(create_element(BrokenRender), c)
    assert _text(c) == ""


def test_doesnt_get_into_inconsistent_state_during_reorders() -> None:
    global _fail_reorder_render
    c = Container()
    _fail_reorder_render = False
    legacy_render(create_element(ErrorBoundary, {"key": "eb"}, *_shuffled_error_boundary_children()), c)
    assert "Caught an error" not in _text(c)

    _fail_reorder_render = True
    legacy_render(create_element(ErrorBoundary, {"key": "eb"}, *_shuffled_error_boundary_children()), c)
    assert _text(c) == "Caught an error: Hello."


def test_catches_errors_in_componentdidmount() -> None:
    c = Container()
    legacy_render(
        create_element(ErrorBoundary, {"key": "eb"}, create_element(BrokenComponentDidMount, {"key": "broken"})),
        c,
    )
    assert _text(c) == "Caught an error: Hello."


def test_catches_errors_in_componentdidupdate() -> None:
    c = Container()
    el = create_element(ErrorBoundary, {"key": "eb"}, create_element(BrokenComponentDidUpdate, {"key": "broken"}))
    legacy_render(el, c)
    legacy_render(el, c)
    assert _text(c) == "Caught an error: Hello."
