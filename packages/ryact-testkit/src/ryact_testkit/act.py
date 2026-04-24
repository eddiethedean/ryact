from __future__ import annotations

import warnings
from collections.abc import Callable, Generator
from contextlib import contextmanager

_act_environment_enabled = False


def set_act_environment_enabled(value: bool) -> None:
    global _act_environment_enabled
    _act_environment_enabled = bool(value)


@contextmanager
def act(flush: Callable[[], None] | None = None) -> Generator[None, None, None]:
    """
    Minimal `act()` equivalent for early translated tests.

    As the scheduler/reconciler grows, this becomes the single chokepoint
    for flushing pending work in a deterministic way.
    """
    if not _act_environment_enabled:
        warnings.warn(
            "The current testing environment is not configured to support act(...).",
            RuntimeWarning,
            stacklevel=2,
        )
    try:
        yield
    finally:
        if flush is not None:
            flush()
