from __future__ import annotations

from collections.abc import Callable, Generator
from contextlib import contextmanager

from ryact.act import (
    act_scope,
    is_act_environment_enabled,
    set_act_environment_enabled as _set_act_environment_enabled,
)

from .warnings import emit_warning


def set_act_environment_enabled(value: bool) -> None:
    _set_act_environment_enabled(value)


@contextmanager
def act(flush: Callable[[], None] | None = None) -> Generator[None, None, None]:
    """
    Minimal `act()` equivalent for early translated tests.

    As the scheduler/reconciler grows, this becomes the single chokepoint
    for flushing pending work in a deterministic way.
    """
    if not is_act_environment_enabled():
        emit_warning(
            "The current testing environment is not configured to support act(...).",
            category=RuntimeWarning,
            stacklevel=2,
        )
    with act_scope():
        try:
            yield
        finally:
            if flush is not None:
                flush()
