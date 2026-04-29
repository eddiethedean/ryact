from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from .concurrent import Suspend, Thenable


@runtime_checkable
class _ThenableLike(Protocol):
    def then(self, cb: Any) -> Any: ...


def use(value: Any) -> Any:
    """
    Experimental `use()` surface (Phase 3).

    Minimal behavior:
    - If passed a Thenable-like object, suspend while pending, return value when fulfilled,
      and throw when rejected.
    - Otherwise return the value as-is.
    """
    if isinstance(value, Thenable) or isinstance(value, _ThenableLike):
        t = value if isinstance(value, Thenable) else value
        # Only our internal Thenable supports status/value/error today.
        if isinstance(t, Thenable):
            if t.status == "pending":
                raise Suspend(t)
            if t.status == "rejected":
                raise t.error
            return t.value
        # Fallback: treat unknown thenables as suspending.
        raise Suspend(value)  # type: ignore[arg-type]
    return value

