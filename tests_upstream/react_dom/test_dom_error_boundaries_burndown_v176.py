# Translated from: packages/react-dom/src/__tests__/ReactErrorBoundaries-test.internal.js
# Burndown v176: final ReactErrorBoundaries createRoot robustness cases.
from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest
from ryact import Component, create_element
from ryact.dev import is_dev, set_dev
from ryact_dom.dom import Container
from ryact_dom.dom_internals import reset_component_dom_registry
from ryact_dom.legacy_mount import batched_updates, reset_legacy_mount_state
from ryact_dom.root import Root, create_root
from ryact_testkit import act, set_act_environment_enabled


@pytest.fixture(autouse=True)
def _dev_and_act() -> Iterator[None]:
    prev = is_dev()
    set_dev(True)
    set_act_environment_enabled(True)
    reset_legacy_mount_state()
    reset_component_dom_registry()
    yield
    reset_legacy_mount_state()
    reset_component_dom_registry()
    set_dev(prev)


def _text(c: Container) -> str:
    return c.text_content


def _render(container: Container, element: object) -> Root:
    root = create_root(container)
    with act(flush=root.flush_sync):
        root.render(element)
    return root


class ErrorBoundary(Component):
    def __init__(self, **props: object) -> None:
        super().__init__(**props)
        self._state: dict[str, Any] = {"error": None}

    @staticmethod
    def getDerivedStateFromError(error: BaseException) -> dict[str, Any]:  # noqa: N802
        return {"error": error}

    def render(self) -> object:
        err = self.state.get("error")
        if err is not None:
            return create_element("span", None, f"Caught an error: {err}.")
        children = self.props.get("children")
        if isinstance(children, tuple):
            from ryact import Fragment

            return create_element(Fragment, None, *children)
        return children


class EvilErrorBoundary(Component):
    @property
    def componentDidCatch(self) -> object:  # noqa: N802
        raise RuntimeError("gotta catch em all")

    def render(self) -> object:
        return self.props.get("children")


def test_propagates_uncaught_error_inside_unbatched_initial_mount() -> None:
    class Foo(Component):
        def render(self) -> object:
            raise RuntimeError("foo error")

    c = Container()
    root = create_root(c)
    with pytest.raises(RuntimeError, match="foo error"):
        batched_updates(lambda: root.render(create_element(Foo)))


def test_should_catch_errors_from_errors_in_the_throw_phase_from_boundaries() -> None:
    def Throws(**_props: object) -> object:
        raise RuntimeError("original error")

    c = Container()
    _render(
        c,
        create_element(
            ErrorBoundary,
            None,
            create_element(EvilErrorBoundary, None, create_element(Throws)),
        ),
    )
    assert "Caught an error: gotta catch em all" in _text(c)


def test_should_catch_errors_from_invariants_in_completion_phase() -> None:
    c = Container()
    _render(
        c,
        create_element(ErrorBoundary, None, create_element("input", None, "child")),
    )
    assert "Caught an error: input is a void element tag" in _text(c)


def test_should_protect_errors_from_errors_in_the_stack_generation(monkeypatch: pytest.MonkeyPatch) -> None:
    from ryact_dom import error_reporting as er

    def Throws(**_props: object) -> object:
        raise RuntimeError("gotta catch em all")

    orig_log = er.log_boundary_component_error

    def evil_log(container: object, err: BaseException, *, boundary_name: str) -> None:
        orig_log(container, err, boundary_name=boundary_name)
        raise RuntimeError("gotta catch em all")

    monkeypatch.setattr(er, "log_boundary_component_error", evil_log)

    c = Container()
    root = create_root(c)
    with pytest.raises(RuntimeError, match="gotta catch em all"), act(flush=root.flush_sync):
        root.render(create_element(ErrorBoundary, None, create_element(Throws)))
    assert "Caught an error: gotta catch em all." in _text(c)
