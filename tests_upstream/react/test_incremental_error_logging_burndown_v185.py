# Translated from: packages/react-reconciler/src/__tests__/ReactIncrementalErrorLogging-test.js
# Burndown v185: lazy init errors attribute Suspense/Activity boundaries, not internal wrappers.
from __future__ import annotations

from ryact import activity, create_element
from ryact.concurrent import lazy
from ryact_testkit import create_noop_root
from ryact_testkit.warnings import WarningCapture


def _lazy_that_throws() -> object:
    raise RuntimeError("lazy init error")


def _render_lazy_in_boundary(boundary: object) -> tuple[list[BaseException], list[str]]:
    uncaught: list[BaseException] = []
    root = create_noop_root()
    root.container.uncaught_error_reporter = uncaught.append  # type: ignore[attr-defined]

    with WarningCapture() as wc:
        try:
            root.render(boundary)
            root.flush()
        except RuntimeError:
            pass

    warnings = [str(record.message) for record in wc.records]
    return uncaught, warnings


def test_does_not_report_internal_offscreen_for_lazy_error_inside_suspense() -> None:
    boundary = create_element(
        "__suspense__",
        {"fallback": create_element("div"), "children": (create_element(lazy(_lazy_that_throws)),)},
    )
    uncaught, warnings = _render_lazy_in_boundary(boundary)

    assert len(uncaught) >= 1
    assert all(str(err) == "lazy init error" or "lazy init error" in str(err) for err in uncaught)
    assert any("An error occurred in the <Suspense> component." in msg for msg in warnings)


def test_does_not_report_internal_offscreen_for_lazy_error_inside_activity() -> None:
    boundary = activity(children=create_element(lazy(_lazy_that_throws)))
    uncaught, warnings = _render_lazy_in_boundary(boundary)

    assert len(uncaught) >= 1
    assert all(str(err) == "lazy init error" or "lazy init error" in str(err) for err in uncaught)
    assert any("An error occurred in the <Activity> component." in msg for msg in warnings)
