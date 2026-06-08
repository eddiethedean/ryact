# Translated from: packages/react-dom/src/__tests__/ReactLegacyErrorBoundaries-test.internal.js
# Burndown v169: legacy error boundaries — update-phase catch, multi-root, mount abort.
from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest
from ryact import Component, Fragment, create_element, create_ref
from ryact.dev import is_dev, set_dev
from ryact_dom.dom import Container
from ryact_dom.dom_internals import reset_component_dom_registry
from ryact_dom.legacy_mount import legacy_render, reset_legacy_mount_state, unmount_component_at_node


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


class BrokenComponentWillUpdate(Component):
    def render(self) -> object:
        return create_element("span", None, "x")

    def UNSAFE_componentWillUpdate(self, *_args: object) -> None:  # noqa: N802
        raise RuntimeError("Hello")


class BrokenComponentWillUnmount(Component):
    def componentWillUnmount(self) -> None:  # noqa: N802
        raise RuntimeError("Hello")

    def render(self) -> object:
        return create_element("span", None, "x")


class Normal(Component):
    def __init__(self, **props: object) -> None:
        super().__init__(**props)
        self._log_name = str(props.get("logName", "Normal"))

    def render(self) -> object:
        return create_element("span", None, self._log_name)


class ErrorMessage(Component):
    def render(self) -> object:
        return create_element("span", None, f"Caught an error: {self.props.get('message')}.")


class ErrorBoundary(Component):
    def __init__(self, **props: object) -> None:
        super().__init__(**props)
        self._state: dict[str, Any] = {"error": None}

    def componentDidCatch(self, error: BaseException) -> None:  # noqa: N802
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


def _render_error_message(error: BaseException, _props: object) -> object:
    return create_element(ErrorMessage, {"message": str(error)})


def test_catches_if_child_throws_in_constructor_during_update() -> None:
    c = Container()
    legacy_render(create_element(ErrorBoundary, {"key": "eb"}, create_element(Normal, {"key": "n"})), c)
    legacy_render(
        create_element(
            ErrorBoundary,
            {"key": "eb"},
            create_element(Normal, {"key": "n"}),
            create_element(Normal, {"key": "n2", "logName": "Normal2"}),
            create_element(BrokenConstructor, {"key": "broken"}),
        ),
        c,
    )
    assert _text(c) == "Caught an error: Hello."


def test_catches_if_child_throws_in_componentwillmount_during_update() -> None:
    c = Container()
    legacy_render(create_element(ErrorBoundary, {"key": "eb"}, create_element(Normal, {"key": "n"})), c)
    legacy_render(
        create_element(
            ErrorBoundary,
            {"key": "eb"},
            create_element(Normal, {"key": "n"}),
            create_element(Normal, {"key": "n2", "logName": "Normal2"}),
            create_element(BrokenComponentWillMount, {"key": "broken"}),
        ),
        c,
    )
    assert _text(c) == "Caught an error: Hello."


def test_catches_if_child_throws_in_componentwillreceiveprops_during_update() -> None:
    c = Container()
    legacy_render(
        create_element(
            ErrorBoundary,
            {"key": "eb"},
            create_element(Normal, {"key": "n"}),
            create_element(BrokenComponentWillReceiveProps, {"key": "broken"}),
        ),
        c,
    )
    legacy_render(
        create_element(
            ErrorBoundary,
            {"key": "eb"},
            create_element(Normal, {"key": "n"}),
            create_element(BrokenComponentWillReceiveProps, {"key": "broken"}),
        ),
        c,
    )
    assert _text(c) == "Caught an error: Hello."


def test_catches_if_child_throws_in_componentwillupdate_during_update() -> None:
    c = Container()
    legacy_render(
        create_element(
            ErrorBoundary,
            {"key": "eb"},
            create_element(Normal, {"key": "n"}),
            create_element(BrokenComponentWillUpdate, {"key": "broken"}),
        ),
        c,
    )
    legacy_render(
        create_element(
            ErrorBoundary,
            {"key": "eb"},
            create_element(Normal, {"key": "n"}),
            create_element(BrokenComponentWillUpdate, {"key": "broken"}),
        ),
        c,
    )
    assert _text(c) == "Caught an error: Hello."


def test_prevents_errors_from_leaking_into_other_roots() -> None:
    c1, c2, c3 = Container(), Container(), Container()
    legacy_render(create_element("span", None, "Before 1"), c1)
    with pytest.raises(RuntimeError, match="Hello"):
        legacy_render(create_element(BrokenRender), c2)
    legacy_render(
        create_element(ErrorBoundary, None, create_element(BrokenRender, {"key": "broken"})),
        c3,
    )
    assert _text(c1) == "Before 1"
    assert _text(c2) == ""
    assert _text(c3) == "Caught an error: Hello."

    legacy_render(create_element("span", None, "After 1"), c1)
    legacy_render(create_element("span", None, "After 2"), c2)
    legacy_render(
        create_element(ErrorBoundary, {"forceRetry": True}, create_element("span", None, "After 3")),
        c3,
    )
    assert _text(c1) == "After 1"
    assert _text(c2) == "After 2"
    assert _text(c3) == "After 3"

    assert unmount_component_at_node(c1) is True
    assert unmount_component_at_node(c2) is True
    assert unmount_component_at_node(c3) is True
    assert _text(c1) == ""
    assert _text(c2) == ""
    assert _text(c3) == ""


def test_does_not_call_componentwillunmount_when_aborting_initial_mount() -> None:
    c = Container()
    legacy_render(
        create_element(
            ErrorBoundary,
            {"key": "eb"},
            create_element(Normal, {"key": "n1"}),
            create_element(BrokenRender, {"key": "broken"}),
            create_element(Normal, {"key": "n2", "logName": "Last"}),
        ),
        c,
    )
    assert _text(c) == "Caught an error: Hello."


def test_doesnt_get_into_inconsistent_state_during_additions() -> None:
    c = Container()
    legacy_render(create_element(ErrorBoundary, {"key": "eb"}), c)
    legacy_render(
        create_element(
            ErrorBoundary,
            {"key": "eb"},
            create_element(Normal, {"key": "n1"}),
            create_element(BrokenRender, {"key": "broken"}),
            create_element(Normal, {"key": "n2", "logName": "Last"}),
        ),
        c,
    )
    assert _text(c) == "Caught an error: Hello."


def test_catches_errors_originating_downstream() -> None:
    class Stateful(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self._fail = False

        def render(self) -> object:
            if self._fail:
                raise RuntimeError("Hello")
            return create_element("div", None, "ok")

    c = Container()
    ref = create_ref()
    legacy_render(
        create_element(ErrorBoundary, None, create_element(Stateful, {"key": "s", "ref": ref})),
        c,
    )
    assert ref.current is not None
    ref.current._fail = True
    ref.current.force_update()
    assert _text(c) == "Caught an error: Hello."


def test_mounts_the_error_message_if_mounting_fails() -> None:
    c = Container()
    legacy_render(
        create_element(
            ErrorBoundary,
            {"renderError": _render_error_message},
            create_element(BrokenRender, {"key": "broken"}),
        ),
        c,
    )
    assert _text(c) == "Caught an error: Hello."


def test_does_not_swallow_exceptions_on_unmounting_without_boundaries() -> None:
    c = Container()
    legacy_render(create_element(BrokenComponentWillUnmount, {"key": "broken"}), c)
    with pytest.raises(RuntimeError, match="Hello"):
        unmount_component_at_node(c)
