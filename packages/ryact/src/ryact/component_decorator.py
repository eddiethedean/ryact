from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from typing import ParamSpec, TypeVar

P = ParamSpec("P")
R = TypeVar("R")


def component(fn: Callable[P, R]) -> Callable[P, R]:
    """
    Optional decorator for function components.

    This preserves the callable signature for type-checkers and improves error
    messages without changing runtime semantics.
    """

    @wraps(fn)
    def wrapped(*args: P.args, **kwargs: P.kwargs) -> R:
        try:
            return fn(*args, **kwargs)
        except BaseException as e:
            name = getattr(fn, "__qualname__", getattr(fn, "__name__", "component"))
            raise RuntimeError(f"Error while rendering component {name}") from e

    return wrapped
