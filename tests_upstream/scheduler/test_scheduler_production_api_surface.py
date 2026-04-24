from __future__ import annotations

from schedulyr.production_scheduler import (
    unstable_get_current_priority_level,
    unstable_next,
    unstable_run_with_priority,
    unstable_wrap_callback,
)
from schedulyr.scheduler import (
    IDLE_PRIORITY,
    IMMEDIATE_PRIORITY,
    LOW_PRIORITY,
    NORMAL_PRIORITY,
    USER_BLOCKING_PRIORITY,
)


def test_default_current_priority_is_normal() -> None:
    assert unstable_get_current_priority_level() == NORMAL_PRIORITY


def test_run_with_priority_sets_and_restores() -> None:
    before = unstable_get_current_priority_level()
    seen: list[int] = []

    def inner() -> None:
        seen.append(unstable_get_current_priority_level())

    unstable_run_with_priority(USER_BLOCKING_PRIORITY, inner)
    assert seen == [USER_BLOCKING_PRIORITY]
    assert unstable_get_current_priority_level() == before


def test_next_shifts_high_priorities_down_to_normal() -> None:
    seen: list[int] = []

    def record() -> None:
        seen.append(unstable_get_current_priority_level())

    unstable_run_with_priority(IMMEDIATE_PRIORITY, lambda: unstable_next(record))
    unstable_run_with_priority(USER_BLOCKING_PRIORITY, lambda: unstable_next(record))
    unstable_run_with_priority(NORMAL_PRIORITY, lambda: unstable_next(record))
    assert seen == [NORMAL_PRIORITY, NORMAL_PRIORITY, NORMAL_PRIORITY]


def test_next_keeps_low_and_idle_priorities() -> None:
    seen: list[int] = []

    def record() -> None:
        seen.append(unstable_get_current_priority_level())

    unstable_run_with_priority(LOW_PRIORITY, lambda: unstable_next(record))
    unstable_run_with_priority(IDLE_PRIORITY, lambda: unstable_next(record))
    assert seen == [LOW_PRIORITY, IDLE_PRIORITY]


def test_wrap_callback_captures_parent_priority() -> None:
    seen: list[int] = []

    def cb() -> None:
        seen.append(unstable_get_current_priority_level())

    def outer() -> None:
        wrapped = unstable_wrap_callback(cb)
        # Run under a different priority; wrapped should restore the captured one.
        unstable_run_with_priority(IMMEDIATE_PRIORITY, wrapped)

    unstable_run_with_priority(USER_BLOCKING_PRIORITY, outer)
    assert seen == [USER_BLOCKING_PRIORITY]

