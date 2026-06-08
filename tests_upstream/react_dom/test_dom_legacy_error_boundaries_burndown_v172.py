# Translated from: packages/react-dom/src/__tests__/ReactLegacyErrorBoundaries-test.internal.js
# Burndown v172: final legacy error boundaries — multi-catch, gsbu errors, context cWM.
from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest
from ryact import Component, Fragment, create_element
from ryact.dev import is_dev, set_dev
from ryact_dom.dom import Container
from ryact_dom.dom_internals import reset_component_dom_registry
from ryact_dom.legacy_mount import legacy_render, reset_legacy_mount_state
from ryact_testkit import WarningCapture


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


def _aggregate_errors(err: BaseException) -> list[BaseException]:
    errors = getattr(err, "errors", None)
    if errors is not None:
        return list(errors)
    if hasattr(err, "exceptions"):
        return list(err.exceptions)
    return [err]


class BrokenComponentDidUpdate(Component):
    def componentDidUpdate(self, *_args: object) -> None:  # noqa: N802
        raise RuntimeError(str(self.props.get("errorText", "Hello")))

    def render(self) -> object:
        return create_element("span", None, str(self.props.get("tick", "")))


class BrokenComponentWillUnmount(Component):
    def componentWillUnmount(self) -> None:  # noqa: N802
        raise RuntimeError(str(self.props.get("errorText", "Hello")))

    def render(self) -> object:
        return create_element("span", None, "x")


class BrokenComponentWillMountWithContext(Component):
    childContextTypes = {"foo": object}  # type: ignore[attr-defined]

    def getChildContext(self) -> dict[str, int]:  # noqa: N802
        return {"foo": 42}

    def UNSAFE_componentWillMount(self) -> None:  # noqa: N802
        raise RuntimeError("Hello")

    def render(self) -> object:
        return self.props.get("children")


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
            render_error = self.props.get("renderError")
            if callable(render_error):
                return render_error(err, self.props)
            return create_element("span", None, f"Caught an error: {err}.")
        children = self.props.get("children")
        if isinstance(children, tuple):
            return create_element(Fragment, None, *children)
        return children


def _render_unmount_error(error: BaseException, _props: object) -> object:
    return create_element("span", None, f"Caught an unmounting error: {error}.")


def _render_update_error(error: BaseException, _props: object) -> object:
    return create_element("span", None, f"Caught an updating error: {error}.")


def test_renders_an_error_state_if_context_provider_throws_in_componentwillmount() -> None:
    c = Container()
    with WarningCapture() as cap:
        legacy_render(
            create_element(
                ErrorBoundary,
                {"key": "eb"},
                create_element(
                    BrokenComponentWillMountWithContext,
                    {"key": "broken"},
                    create_element("span", None, "x"),
                ),
            ),
            c,
        )
    assert _text(c) == "Caught an error: Hello."
    assert any("childContextTypes" in str(r.message) for r in cap.records)


def test_handles_errors_that_occur_in_before_mutation_commit_hook() -> None:
    errors_log: list[str] = []

    class Parent(Component):
        def getSnapshotBeforeUpdate(self, *_args: object) -> None:  # noqa: N802
            errors_log.append("parent sad")
            raise RuntimeError("parent sad")

        def componentDidUpdate(self, *_args: object) -> None:  # noqa: N802
            pass

        def render(self) -> object:
            return create_element(Child, {"n": self.props.get("n")})

    class Child(Component):
        def getSnapshotBeforeUpdate(self, *_args: object) -> None:  # noqa: N802
            errors_log.append("child sad")
            raise RuntimeError("child sad")

        def componentDidUpdate(self, *_args: object) -> None:  # noqa: N802
            pass

        def render(self) -> object:
            return create_element("span", None, str(self.props.get("n")))

    c = Container()
    legacy_render(create_element(Parent, {"n": 0}), c)
    with pytest.raises(BaseException) as excinfo:
        legacy_render(create_element(Parent, {"n": 1}), c)
    caught = _aggregate_errors(excinfo.value)
    assert [str(e) for e in caught] == ["child sad", "parent sad"]
    assert errors_log == ["child sad", "parent sad"]


def test_calls_componentdidcatch_for_each_error_that_is_captured() -> None:
    tick = {"v": 0}

    def _child(key: str, cls: type[Component], text: str) -> object:
        return create_element(cls, {"key": key, "errorText": text, "tick": tick["v"]})

    c = Container()
    legacy_render(
        create_element(
            ErrorBoundary,
            {"key": "outer"},
            create_element(
                ErrorBoundary,
                {"key": "unmount", "renderError": _render_unmount_error},
                _child("u1", BrokenComponentWillUnmount, "E1"),
                _child("u2", BrokenComponentWillUnmount, "E2"),
            ),
            create_element(
                ErrorBoundary,
                {"key": "update", "renderError": _render_update_error},
                _child("d1", BrokenComponentDidUpdate, "E3"),
                _child("d2", BrokenComponentDidUpdate, "E4"),
            ),
        ),
        c,
    )

    legacy_render(
        create_element(
            ErrorBoundary,
            {"key": "outer"},
            create_element(
                ErrorBoundary,
                {"key": "unmount", "renderError": _render_unmount_error},
                _child("u1", BrokenComponentWillUnmount, "E1"),
            ),
            create_element(
                ErrorBoundary,
                {"key": "update", "renderError": _render_update_error},
                _child("d1", BrokenComponentDidUpdate, "E3"),
            ),
        ),
        c,
    )
    unmount_boundary = c._ryact_dom_root._class_instances[(ErrorBoundary, "unmount")]
    assert unmount_boundary._did_catch_errors == ["E1", "E2"]
    assert "Caught an unmounting error: E2." in _text(c)

    tick["v"] = 1
    c2 = Container()
    legacy_render(
        create_element(
            ErrorBoundary,
            {"key": "update", "renderError": _render_update_error},
            _child("d1", BrokenComponentDidUpdate, "E3"),
            _child("d2", BrokenComponentDidUpdate, "E4"),
        ),
        c2,
    )
    legacy_render(
        create_element(
            ErrorBoundary,
            {"key": "update", "renderError": _render_update_error},
            _child("d1", BrokenComponentDidUpdate, "E3"),
            _child("d2", BrokenComponentDidUpdate, "E4"),
        ),
        c2,
    )
    update_boundary = c2._ryact_dom_root._class_instances[(ErrorBoundary, "update")]
    assert update_boundary._did_catch_errors == ["E3", "E4"]
    assert _text(c2) == "Caught an updating error: E4."
