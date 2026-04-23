from __future__ import annotations

from collections.abc import Callable, Generator
from contextlib import contextmanager


@contextmanager
def act(flush: Callable[[], None] | None = None) -> Generator[None, None, None]:
    """
    Minimal `act()` equivalent for early translated tests.

    As the scheduler/reconciler grows, this becomes the single chokepoint
    for flushing pending work in a deterministic way.
    """
    try:
        yield
    finally:
        if flush is not None:
            flush()
