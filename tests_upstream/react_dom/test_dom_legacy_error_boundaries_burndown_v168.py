# Translated from: packages/react-dom/src/__tests__/ReactLegacyErrorBoundaries-test.internal.js
# Burndown v168: legacy error boundaries — catch, recover, noop, uncaught re-raise.
from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest
from ryact import Component, create_element
from ryact.dev import is_dev, set_dev
from ryact_dom.dom import Container
from ryact_dom.dom_internals import reset_component_dom_registry
from ryact_dom.error_reporting import LEGACY_RENDER_DEPRECATION, console_error_log
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


@pytest.fixture
def container() -> Container:
    c = Container()
    c.console_error_log = []  # type: ignore[attr-defined]
    c.window_error_log = []  # type: ignore[attr-defined]
    return c


def _text(c: Container) -> str:
    return c.text_content


def _console_strs(c: Container) -> list[str]:
    out: list[str] = []
    for item in console_error_log(c):
        if isinstance(item, BaseException):
            out.append(str(item))
        elif isinstance(item, str):
            out.append(item)
        elif isinstance(item, tuple):
            out.extend(str(x) for x in item)
    return out


class BrokenRender(Component):
    def render(self) -> object:
        raise RuntimeError("Hello")


class BrokenConstructor(Component):
    def __init__(self, **props: object) -> None:
        super().__init__(**props)
        raise RuntimeError("Hello")

    def render(self) -> object:
        return None


class BrokenComponentWillMount(Component):
    def UNSAFE_componentWillMount(self) -> None:  # noqa: N802
        raise RuntimeError("Hello")

    def render(self) -> object:
        return None


class BrokenComponentWillReceiveProps(Component):
    def render(self) -> object:
        return create_element("span", None, "x")

    def UNSAFE_componentWillReceiveProps(self, *_args: object) -> None:  # noqa: N802
        raise RuntimeError("Hello")


class BrokenComponentDidUpdate(Component):
    def render(self) -> object:
        return create_element("span", None, "x")

    def componentDidUpdate(self, *_args: object) -> None:  # noqa: N802
        raise RuntimeError("Hello")


class BrokenComponentDidMount(Component):
    def componentDidMount(self) -> None:  # noqa: N802
        raise RuntimeError("Hello")

    def render(self) -> object:
        return None


class BrokenComponentWillUpdate(Component):
    def render(self) -> object:
        return create_element("span", None, "x")

    def UNSAFE_componentWillUpdate(self, *_args: object) -> None:  # noqa: N802
        raise RuntimeError("Hello")


class Normal(Component):
    def __init__(self, **props: object) -> None:
        super().__init__(**props)
        self._log_name = str(props.get("logName", "Normal"))

    def render(self) -> object:
        return create_element("span", None, self._log_name)


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
            return create_element("div", None, *children) if children else None
        return create_element("div", None, children)


class BothErrorBoundaries(Component):
    def __init__(self, **props: object) -> None:
        super().__init__(**props)
        self._state: dict[str, Any] = {"error": None}

    @staticmethod
    def getDerivedStateFromError(error: BaseException) -> dict[str, Any]:  # noqa: N802
        return {"error": error}

    def componentDidCatch(self, error: BaseException) -> None:  # noqa: N802
        self.set_state({"error": error})

    def render(self) -> object:
        err = self.state.get("error")
        if err is not None:
            return create_element("span", None, f"Caught an error: {err}.")
        children = self.props.get("children")
        if isinstance(children, tuple):
            return create_element("div", None, *children) if children else None
        return create_element("div", None, children)


class NoopErrorBoundary(Component):
    def componentDidCatch(self, _error: BaseException) -> None:  # noqa: N802
        pass

    def render(self) -> object:
        return create_element(BrokenRender)


def test_does_not_swallow_exceptions_on_mounting_without_boundaries(container: Container) -> None:
    for el in (
        create_element(BrokenRender),
        create_element(BrokenComponentWillMount),
        create_element(BrokenComponentDidMount),
    ):
        c = Container()
        with pytest.raises(RuntimeError, match="Hello"):
            legacy_render(el, c)


def test_does_not_swallow_exceptions_on_updating_without_boundaries(container: Container) -> None:
    for broken in (BrokenComponentWillUpdate, BrokenComponentWillReceiveProps, BrokenComponentDidUpdate):
        c = Container()
        legacy_render(create_element(broken), c)
        with pytest.raises(RuntimeError, match="Hello"):
            legacy_render(create_element(broken), c)


def test_logs_a_single_error_using_both_error_boundaries(container: Container) -> None:
    legacy_render(create_element(BothErrorBoundaries, None, create_element(BrokenRender)), container)
    msgs = _console_strs(container)
    assert _text(container) == "Caught an error: Hello."
    assert any(LEGACY_RENDER_DEPRECATION in m for m in msgs)
    assert any("The above error occurred in the" in m for m in msgs)
    assert any("Hello" in m for m in msgs)


def test_renders_an_error_state_if_child_throws_in_render(container: Container) -> None:
    legacy_render(create_element(ErrorBoundary, None, create_element(BrokenRender)), container)
    assert _text(container) == "Caught an error: Hello."


def test_renders_an_error_state_if_child_throws_in_constructor(container: Container) -> None:
    legacy_render(create_element(ErrorBoundary, None, create_element(BrokenConstructor)), container)
    assert _text(container) == "Caught an error: Hello."


def test_renders_an_error_state_if_child_throws_in_componentwillmount(container: Container) -> None:
    legacy_render(create_element(ErrorBoundary, None, create_element(BrokenComponentWillMount)), container)
    assert _text(container) == "Caught an error: Hello."


def test_successfully_mounts_if_no_error_occurs(container: Container) -> None:
    legacy_render(
        create_element(ErrorBoundary, None, create_element("div", None, "Mounted successfully.")),
        container,
    )
    assert _text(container) == "Mounted successfully."


def test_renders_empty_output_if_error_boundary_does_not_handle_the_error(container: Container) -> None:
    legacy_render(
        create_element("div", None, "Sibling", create_element(NoopErrorBoundary)),
        container,
    )
    msgs = _console_strs(container)
    assert _text(container) == "Sibling"
    assert any("NoopErrorBoundary: Error boundaries should implement getDerivedStateFromError()" in m for m in msgs)


def test_can_recover_from_error_state(container: Container) -> None:
    legacy_render(create_element(ErrorBoundary, None, create_element(BrokenRender)), container)
    legacy_render(create_element(ErrorBoundary, None, create_element(BrokenRender)), container)
    assert _text(container) == "Caught an error: Hello."

    legacy_render(
        create_element(ErrorBoundary, {"forceRetry": True}, create_element(Normal)),
        container,
    )
    assert "Caught an error" not in _text(container)
    assert _text(container) == "Normal"


def test_can_update_multiple_times_in_error_state(container: Container) -> None:
    legacy_render(create_element(ErrorBoundary, None, create_element(BrokenRender)), container)
    assert _text(container) == "Caught an error: Hello."

    legacy_render(create_element(ErrorBoundary, None, create_element(BrokenRender)), container)
    assert _text(container) == "Caught an error: Hello."

    legacy_render(create_element("div", None, "Other screen"), container)
    assert _text(container) == "Other screen"


def test_catches_if_child_throws_in_render_during_update(container: Container) -> None:
    legacy_render(create_element(ErrorBoundary, None, create_element(Normal)), container)
    legacy_render(
        create_element(
            ErrorBoundary,
            None,
            create_element(Normal),
            create_element(Normal, {"logName": "Normal2"}),
            create_element(BrokenRender),
        ),
        container,
    )
    assert _text(container) == "Caught an error: Hello."
