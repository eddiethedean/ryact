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
    # Upstream: ReactIncrementalErrorLogging-test.js
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
    # Upstream: ReactIncrementalErrorLogging-test.js
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
    # Upstream: ReactIncrementalErrorLogging-test.js
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


def test_resets_instance_variables_before_unmounting_failed_node() -> None:
    # Upstream: ReactIncrementalErrorLogging-test.js
    # "resets instance variables before unmounting failed node"
    log: list[str] = []

    class ErrorBoundary(Component):
        def componentDidCatch(self, _err: BaseException) -> None:  # noqa: N802
            self.set_state({"error": True})

        def render(self) -> object:
            if bool(self.state.get("error")):
                return None
            return _only_child(self.props["children"])

    class Foo(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self.set_state({"step": 0})

        def componentDidMount(self) -> None:  # noqa: N802
            self.set_state({"step": 1})

        def componentWillUnmount(self) -> None:  # noqa: N802
            log.append(f"componentWillUnmount: {self.state['step']}")

        def render(self) -> object:
            log.append(f"render: {self.state['step']}")
            if int(self.state["step"]) > 0:
                raise RuntimeError("oops")
            return None

    root = create_noop_root()
    root.render(create_element(ErrorBoundary, {"children": create_element(Foo)}))
    # componentDidMount schedules an update; flush it.
    root.flush()

    assert log == [
        "render: 0",
        "render: 1",
        "render: 1",
        "componentWillUnmount: 0",
    ]

