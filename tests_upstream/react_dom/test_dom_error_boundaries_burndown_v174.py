# Translated from: packages/react-dom/src/__tests__/ReactErrorBoundaries-test.internal.js
# Burndown v174: createRoot error boundaries — update-phase catch, multi-root, propagation, refs.
from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest
from ryact import Component, Fragment, create_element, create_ref
from ryact.dev import is_dev, set_dev
from ryact_dom.dom import Container, ElementNode
from ryact_dom.dom_internals import reset_component_dom_registry
from ryact_dom.error_reporting import console_error_log, window_error_log
from ryact_dom.root import Root, create_root
from ryact_testkit import act, set_act_environment_enabled


@pytest.fixture(autouse=True)
def _dev_and_act() -> Iterator[None]:
    prev = is_dev()
    set_dev(True)
    set_act_environment_enabled(True)
    reset_component_dom_registry()
    yield
    reset_component_dom_registry()
    set_dev(prev)


def _text(c: Container) -> str:
    return c.text_content


def _has_logged_hello(c: Container) -> bool:
    for item in console_error_log(c) + window_error_log(c):
        if isinstance(item, BaseException) and str(item) == "Hello":
            return True
        if isinstance(item, tuple) and any(str(x) == "Hello" for x in item):
            return True
    return False


def _render(container: Container, element: object) -> Root:
    root = create_root(container)
    with act(flush=root.flush_sync):
        root.render(element)
    return root


def _update(root: Root, element: object) -> None:
    with act(flush=root.flush_sync):
        root.render(element)


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
            ref = self.props.get("errorMessageRef")
            return create_element("span", {"ref": ref}, f"Caught an error: {err}.")
        children = self.props.get("children")
        if isinstance(children, tuple):
            return create_element(Fragment, None, *children)
        return children


def _render_error_message(error: BaseException, _props: object) -> object:
    return create_element(ErrorMessage, {"message": str(error)})


def test_catches_if_child_throws_in_constructor_during_update() -> None:
    c = Container()
    root = _render(c, create_element(ErrorBoundary, {"key": "eb"}, create_element(Normal, {"key": "n"})))
    _update(
        root,
        create_element(
            ErrorBoundary,
            {"key": "eb"},
            create_element(Normal, {"key": "n"}),
            create_element(Normal, {"key": "n2", "logName": "Normal2"}),
            create_element(BrokenConstructor, {"key": "broken"}),
        ),
    )
    assert _text(c) == "Caught an error: Hello."


def test_catches_if_child_throws_in_componentwillmount_during_update() -> None:
    c = Container()
    root = _render(c, create_element(ErrorBoundary, {"key": "eb"}, create_element(Normal, {"key": "n"})))
    _update(
        root,
        create_element(
            ErrorBoundary,
            {"key": "eb"},
            create_element(Normal, {"key": "n"}),
            create_element(Normal, {"key": "n2", "logName": "Normal2"}),
            create_element(BrokenComponentWillMount, {"key": "broken"}),
        ),
    )
    assert _text(c) == "Caught an error: Hello."


def test_catches_if_child_throws_in_componentwillreceiveprops_during_update() -> None:
    c = Container()
    root = _render(
        c,
        create_element(
            ErrorBoundary,
            {"key": "eb"},
            create_element(Normal, {"key": "n"}),
            create_element(BrokenComponentWillReceiveProps, {"key": "broken"}),
        ),
    )
    _update(
        root,
        create_element(
            ErrorBoundary,
            {"key": "eb"},
            create_element(Normal, {"key": "n"}),
            create_element(BrokenComponentWillReceiveProps, {"key": "broken"}),
        ),
    )
    assert _text(c) == "Caught an error: Hello."


def test_catches_if_child_throws_in_componentwillupdate_during_update() -> None:
    c = Container()
    root = _render(
        c,
        create_element(
            ErrorBoundary,
            {"key": "eb"},
            create_element(Normal, {"key": "n"}),
            create_element(BrokenComponentWillUpdate, {"key": "broken"}),
        ),
    )
    _update(
        root,
        create_element(
            ErrorBoundary,
            {"key": "eb"},
            create_element(Normal, {"key": "n"}),
            create_element(BrokenComponentWillUpdate, {"key": "broken"}),
        ),
    )
    assert _text(c) == "Caught an error: Hello."


def test_prevents_errors_from_leaking_into_other_roots() -> None:
    c1, c2, c3 = Container(), Container(), Container()
    root1 = _render(c1, create_element("span", None, "Before 1"))
    c2.console_error_log = []  # type: ignore[attr-defined]
    root2 = _render(c2, create_element(BrokenRender))
    root3 = _render(
        c3,
        create_element(ErrorBoundary, None, create_element(BrokenRender, {"key": "broken"})),
    )
    assert _text(c1) == "Before 1"
    assert _text(c2) == ""
    assert _has_logged_hello(c2)
    assert _text(c3) == "Caught an error: Hello."

    _update(root1, create_element("span", None, "After 1"))
    _update(root2, create_element("span", None, "After 2"))
    _update(root3, create_element(ErrorBoundary, {"forceRetry": True}, create_element("span", None, "After 3")))
    assert _text(c1) == "After 1"
    assert _text(c2) == "After 2"
    assert _text(c3) == "After 3"

    with act(flush=root1.flush_sync):
        root1.unmount()
    with act(flush=root2.flush_sync):
        root2.unmount()
    with act(flush=root3.flush_sync):
        root3.unmount()
    assert _text(c1) == ""
    assert _text(c2) == ""
    assert _text(c3) == ""


def test_does_not_call_componentwillunmount_when_aborting_initial_mount() -> None:
    c = Container()
    _render(
        c,
        create_element(
            ErrorBoundary,
            {"key": "eb"},
            create_element(Normal, {"key": "n1"}),
            create_element(BrokenRender, {"key": "broken"}),
            create_element(Normal, {"key": "n2", "logName": "Last"}),
        ),
    )
    assert _text(c) == "Caught an error: Hello."


def test_doesnt_get_into_inconsistent_state_during_additions() -> None:
    c = Container()
    root = _render(c, create_element(ErrorBoundary, {"key": "eb"}))
    _update(
        root,
        create_element(
            ErrorBoundary,
            {"key": "eb"},
            create_element(Normal, {"key": "n1"}),
            create_element(BrokenRender, {"key": "broken"}),
            create_element(Normal, {"key": "n2", "logName": "Last"}),
        ),
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
    root = _render(
        c,
        create_element(ErrorBoundary, None, create_element(Stateful, {"key": "s", "ref": ref})),
    )
    assert ref.current is not None
    ref.current._fail = True
    with act(flush=root.flush_sync):
        ref.current.force_update()
    assert _text(c) == "Caught an error: Hello."


def test_mounts_the_error_message_if_mounting_fails() -> None:
    c = Container()
    _render(
        c,
        create_element(
            ErrorBoundary,
            {"renderError": _render_error_message},
            create_element(BrokenRender, {"key": "broken"}),
        ),
    )
    assert _text(c) == "Caught an error: Hello."


def test_does_not_swallow_exceptions_on_unmounting_without_boundaries() -> None:
    c = Container()
    c.console_error_log = []  # type: ignore[attr-defined]
    c.window_error_log = []  # type: ignore[attr-defined]
    root = _render(c, create_element(BrokenComponentWillUnmount, {"key": "broken"}))
    with act(flush=root.flush_sync):
        root.unmount()
    assert _has_logged_hello(c)


def test_propagates_errors_on_retry_on_mounting() -> None:
    c = Container()
    _render(
        c,
        create_element(
            ErrorBoundary,
            {"key": "eb"},
            create_element(RetryErrorBoundary, {"key": "retry"}),
            create_element(BrokenRender, {"key": "broken"}),
        ),
    )
    assert _text(c) == "Caught an error: Hello."


def test_propagates_errors_inside_boundary_during_componentwillmount() -> None:
    c = Container()
    _render(
        c,
        create_element(
            ErrorBoundary,
            {"key": "eb"},
            create_element(BrokenComponentWillMountErrorBoundary, {"key": "inner"}),
        ),
    )
    assert _text(c) == "Caught an error: Hello."


def test_propagates_errors_inside_boundary_while_rendering_error_state() -> None:
    c = Container()
    _render(
        c,
        create_element(
            ErrorBoundary,
            {"key": "eb"},
            create_element(
                BrokenRenderErrorBoundary,
                {"key": "inner"},
                create_element(BrokenRender, {"key": "broken"}),
            ),
        ),
    )
    assert _text(c) == "Caught an error: Hello."


def test_propagates_errors_inside_boundary_during_componentdidmount() -> None:
    c = Container()
    _render(
        c,
        create_element(
            ErrorBoundary,
            {"key": "eb"},
            create_element(BrokenComponentDidMountErrorBoundary, {"key": "inner"}),
        ),
    )
    assert _text(c) == "Caught an error: Hello."


def test_discards_a_bad_root_if_the_root_component_fails() -> None:
    c = Container()
    c.console_error_log = []  # type: ignore[attr-defined]
    _render(c, create_element(BrokenRender))
    assert _text(c) == ""
    assert _has_logged_hello(c)


def test_doesnt_get_into_inconsistent_state_during_removals() -> None:
    c = Container()
    root = _render(
        c,
        create_element(
            ErrorBoundary,
            {"key": "eb"},
            create_element("span", {"key": "n"}, "ok"),
            create_element(BrokenComponentWillUnmount, {"key": "broken"}),
        ),
    )
    _update(root, create_element(ErrorBoundary, {"key": "eb"}))
    assert _text(c) == "Caught an error: Hello."


def test_resets_object_refs_if_mounting_aborts() -> None:
    child_ref = create_ref()
    error_ref = create_ref()
    c = Container()
    _render(
        c,
        create_element(
            ErrorBoundary,
            {"key": "eb", "errorMessageRef": error_ref},
            create_element("div", {"key": "d", "ref": child_ref}),
            create_element(BrokenRender, {"key": "broken"}),
        ),
    )
    assert child_ref.current is None
    assert isinstance(error_ref.current, ElementNode)
    assert _text(c) == "Caught an error: Hello."
