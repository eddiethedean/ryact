from __future__ import annotations

from collections.abc import Callable


def make_use_id_allocator(*, identifier_prefix: str = "") -> Callable[[], str]:
    """React ``useId``-style ids (``:rN:`` with optional ``identifierPrefix``)."""

    counter = 0

    def next_id() -> str:
        nonlocal counter
        counter += 1
        if identifier_prefix:
            return f"{identifier_prefix}:r{counter}:"
        return f":r{counter}:"

    return next_id
