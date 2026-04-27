from __future__ import annotations

import pytest

from ryact import Component, create_element
from ryact_testkit import create_noop_root
from ryact_testkit.warnings import WarningCapture


def _only_child(children: object) -> object:
    if isinstance(children, tuple):
        return children[0] if children else None
    return children


def test_should_log_errors_that_occur_during_the_begin_phase() -> None:
    # Upstream: ReactConfigurableErrorLogging-test.js
    # "should log errors that occur during the begin phase"
    class ErrorThrowingComponent(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            raise RuntimeError("constructor error")

        def render(self) -> object:
            return create_element("div")

    root = create_noop_root()
    with WarningCapture() as wc, pytest.raises(RuntimeError, match="constructor error"):
        root.render(create_element(ErrorThrowingComponent))
    wc.assert_any("An error occurred")


def test_should_log_errors_that_occur_during_the_commit_phase() -> None:
    # Upstream: ReactConfigurableErrorLogging-test.js
    # "should log errors that occur during the commit phase"
    class ErrorThrowingComponent(Component):
        def componentDidMount(self) -> None:  # noqa: N802
            raise RuntimeError("componentDidMount error")

        def render(self) -> object:
            return create_element("div")

    root = create_noop_root()
    with WarningCapture() as wc, pytest.raises(RuntimeError, match="componentDidMount error"):
        root.render(create_element(ErrorThrowingComponent))
    wc.assert_any("An error occurred")


def test_should_ignore_errors_thrown_in_log_method_to_prevent_cycle() -> None:
    # Upstream: ReactConfigurableErrorLogging-test.js
    # "should ignore errors thrown in log method to prevent cycle"
    class ErrorBoundary(Component):
        def componentDidCatch(self, _err: BaseException) -> None:  # noqa: N802
            self.set_state({"error": True})

        def render(self) -> object:
            if bool(self.state.get("error")):
                return None
            return _only_child(self.props["children"])

    class ErrorThrowingComponent(Component):
        def render(self) -> object:
            raise RuntimeError("render error")

    root = create_noop_root()
    calls: list[str] = []

    def bad_reporter(_err: BaseException) -> None:
        calls.append("report")
        raise RuntimeError("logCapturedError error")

    root.container.captured_error_reporter = bad_reporter  # type: ignore[attr-defined]
    with pytest.raises(RuntimeError, match="logCapturedError error"):
        root.render(
            create_element(ErrorBoundary, {"children": create_element(ErrorThrowingComponent)})
        )
    assert calls == ["report"]

