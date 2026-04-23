from __future__ import annotations

from contextlib import contextmanager
from typing import Callable, Generator, Optional


@contextmanager
def act(flush: Optional[Callable[[], None]] = None) -> Generator[None, None, None]:
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

