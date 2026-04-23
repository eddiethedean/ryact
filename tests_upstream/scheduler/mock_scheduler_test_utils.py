"""
Synchronous helpers mirroring React ``internal-test-utils`` scheduler helpers
(``waitFor``, ``waitForAll``, ``waitForPaint``, ``assertLog``) for
:class:`schedulyr.mock_scheduler.UnstableMockScheduler`.
"""

from __future__ import annotations

from typing import Any, Optional

from schedulyr.mock_scheduler import UnstableMockScheduler


def _equals(actual: list[Any], expected: list[Any]) -> bool:
    if len(actual) != len(expected):
        return False
    return all(a == b for a, b in zip(actual, expected))


def _diff(expected: list[Any], actual: list[Any]) -> str:
    return f"expected={expected!r}\nactual={actual!r}"


def assert_log(s: UnstableMockScheduler, expected_log: list[Any]) -> None:
    actual = s.unstable_clear_log()
    if not _equals(actual, expected_log):
        raise AssertionError(
            "Expected sequence of events did not occur.\n\n" + _diff(expected_log, actual)
        )


def wait_for(
    s: UnstableMockScheduler,
    expected_log: list[Any],
    *,
    additional_logs_after_attempting_to_yield: Optional[list[Any]] = None,
) -> None:
    """Match React ``waitFor`` (minus real microtasks): incremental ``flushNumberOfYields``."""
    stop_after = len(expected_log)
    actual_log: list[Any] = []
    while True:
        if s.unstable_has_pending_work():
            s.unstable_flush_number_of_yields(stop_after - len(actual_log))
            actual_log.extend(s.unstable_clear_log())
            if len(actual_log) >= stop_after:
                actual_log.extend(s.unstable_clear_log())
                break
        else:
            break

    exp = list(expected_log)
    if additional_logs_after_attempting_to_yield is not None:
        exp.extend(additional_logs_after_attempting_to_yield)

    if not _equals(actual_log, exp):
        raise AssertionError(
            "Expected sequence of events did not occur.\n\n" + _diff(exp, actual_log)
        )


def wait_for_all(s: UnstableMockScheduler, expected_log: list[Any]) -> None:
    while True:
        if not s.unstable_has_pending_work():
            break
        s.unstable_flush_all_without_asserting()
    actual = s.unstable_clear_log()
    if not _equals(actual, expected_log):
        raise AssertionError(
            "Expected sequence of events did not occur.\n\n" + _diff(expected_log, actual)
        )


def wait_for_paint(s: UnstableMockScheduler, expected_log: list[Any]) -> None:
    if s.unstable_has_pending_work():
        s.unstable_flush_until_next_paint()
    actual = s.unstable_clear_log()
    if not _equals(actual, expected_log):
        raise AssertionError(
            "Expected sequence of events did not occur.\n\n" + _diff(expected_log, actual)
        )
