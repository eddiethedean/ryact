# Translated from: packages/react-dom/src/__tests__/ReactDOMConsoleErrorReporting-test.js
# Burndown v161: createRoot console/window error reporting.
from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest
from ryact import Component, create_element
from ryact.dev import is_dev, set_dev
from ryact.hooks import use_effect, use_layout_effect
from ryact_dom.dom import Container, ElementNode
from ryact_dom.error_reporting import console_error_log, window_error_log
from ryact_dom.root import create_root
from ryact_testkit import WarningCapture


@pytest.fixture(autouse=True)
def _dev_on() -> Iterator[None]:
    prev = is_dev()
    set_dev(True)
    yield
    set_dev(prev)


@pytest.fixture
def container() -> Container:
    c = Container()
    c.console_error_log = []  # type: ignore[attr-defined]
    c.window_error_log = []  # type: ignore[attr-defined]
    return c


def _text(c: Container) -> str:
    return c.text_content


def _log_has_boom(log: list[Any]) -> bool:
    for item in log:
        if isinstance(item, BaseException) and "Boom" in str(item):
            return True
        if isinstance(item, tuple) and item and isinstance(item[0], BaseException) and "Boom" in str(item[0]):
            return True
    return False


def _console_strs(c: Container) -> list[str]:
    out: list[str] = []
    for item in console_error_log(c):
        if isinstance(item, BaseException):
            out.append(str(item))
        elif isinstance(item, tuple):
            out.extend(str(x) for x in item)
    return out


class ErrorBoundary(Component):
    def __init__(self, **props: Any) -> None:
        super().__init__(**props)
        self._state = {"error": None}

    @staticmethod
    def getDerivedStateFromError(error: BaseException) -> dict[str, Any]:  # noqa: N802
        return {"error": error}

    def render(self) -> object:
        err = self.state.get("error")
        if err is not None:
            return create_element("span", None, f"Caught: {err}")
        children = self.props.get("children")
        if isinstance(children, tuple):
            return children[0] if children else None
        return children


def test_logs_errors_during_event_handlers(container: Container) -> None:
    def Foo(**props: Any) -> object:
        def on_click(_e: object) -> None:
            raise RuntimeError("Boom")

        return create_element("button", {"onClick": on_click}, "click me")

    root = create_root(container)
    root.render(create_element(Foo))
    btn = container.root.children[0]
    assert isinstance(btn, ElementNode)
    btn.dispatch_event("click")
    assert _log_has_boom(window_error_log(container))
    assert _log_has_boom(console_error_log(container))

    container.console_error_log = []  # type: ignore[attr-defined]
    container.window_error_log = []  # type: ignore[attr-defined]
    root.render(create_element(lambda: create_element("span", None, "OK")))
    assert _text(container) == "OK"
    assert window_error_log(container) == []
    assert console_error_log(container) == []


def test_logs_render_errors_without_an_error_boundary(container: Container) -> None:
    def Foo(**_props: Any) -> object:
        raise RuntimeError("Boom")

    root = create_root(container)
    with WarningCapture() as cap:
        root.render(create_element(Foo))
    assert _log_has_boom(window_error_log(container))
    assert _log_has_boom(console_error_log(container))
    assert any("An error occurred in the component" in str(r.message) for r in cap.records)
    assert any("Consider adding an error boundary" in str(r.message) for r in cap.records)

    container.console_error_log = []  # type: ignore[attr-defined]
    container.window_error_log = []  # type: ignore[attr-defined]
    root.render(create_element(lambda: create_element("span", None, "OK")))
    assert _text(container) == "OK"
    assert window_error_log(container) == []
    assert console_error_log(container) == []


def test_logs_render_errors_with_an_error_boundary(container: Container) -> None:
    def Foo(**_props: Any) -> object:
        raise RuntimeError("Boom")

    root = create_root(container)
    root.render(create_element(ErrorBoundary, {"children": create_element(Foo)}))
    assert window_error_log(container) == []
    msgs = _console_strs(container)
    assert any("Boom" in m for m in msgs)
    assert any("The above error occurred in the" in m for m in msgs)
    assert any("ErrorBoundary" in m for m in msgs)

    container.console_error_log = []  # type: ignore[attr-defined]
    root.render(create_element(lambda: create_element("span", None, "OK")))
    assert _text(container) == "OK"
    assert console_error_log(container) == []


def test_logs_layout_effect_errors_without_an_error_boundary(container: Container) -> None:
    def Foo(**_props: Any) -> None:
        def boom() -> None:
            raise RuntimeError("Boom")

        use_layout_effect(boom, ())
        return None

    root = create_root(container)
    with WarningCapture() as cap:
        root.render(create_element(Foo))
    assert _log_has_boom(window_error_log(container))
    assert _log_has_boom(console_error_log(container))
    assert any("Consider adding an error boundary" in str(r.message) for r in cap.records)

    container.console_error_log = []  # type: ignore[attr-defined]
    container.window_error_log = []  # type: ignore[attr-defined]
    root.render(create_element(lambda: create_element("span", None, "OK")))
    assert _text(container) == "OK"


def test_logs_layout_effect_errors_with_an_error_boundary(container: Container) -> None:
    def Foo(**_props: Any) -> None:
        def boom() -> None:
            raise RuntimeError("Boom")

        use_layout_effect(boom, ())
        return None

    root = create_root(container)
    root.render(create_element(ErrorBoundary, {"children": create_element(Foo)}))
    assert window_error_log(container) == []
    msgs = _console_strs(container)
    assert any("The above error occurred in the" in m for m in msgs)
    assert any("ErrorBoundary" in m for m in msgs)

    container.console_error_log = []  # type: ignore[attr-defined]
    root.render(create_element(lambda: create_element("span", None, "OK")))
    assert _text(container) == "OK"


def test_logs_passive_effect_errors_without_an_error_boundary(container: Container) -> None:
    def Foo(**_props: Any) -> None:
        def boom() -> None:
            raise RuntimeError("Boom")

        use_effect(boom, ())
        return None

    root = create_root(container)
    with WarningCapture() as cap:
        root.render(create_element(Foo))
    assert _log_has_boom(window_error_log(container))
    assert _log_has_boom(console_error_log(container))
    assert any("Consider adding an error boundary" in str(r.message) for r in cap.records)

    container.console_error_log = []  # type: ignore[attr-defined]
    container.window_error_log = []  # type: ignore[attr-defined]
    root.render(create_element(lambda: create_element("span", None, "OK")))
    assert _text(container) == "OK"


def test_logs_passive_effect_errors_with_an_error_boundary(container: Container) -> None:
    def Foo(**_props: Any) -> None:
        def boom() -> None:
            raise RuntimeError("Boom")

        use_effect(boom, ())
        return None

    root = create_root(container)
    root.render(create_element(ErrorBoundary, {"children": create_element(Foo)}))
    assert window_error_log(container) == []
    msgs = _console_strs(container)
    assert any("The above error occurred in the" in m for m in msgs)
    assert any("ErrorBoundary" in m for m in msgs)

    container.console_error_log = []  # type: ignore[attr-defined]
    root.render(create_element(lambda: create_element("span", None, "OK")))
    assert _text(container) == "OK"
