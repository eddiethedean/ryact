from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from .concurrent import Suspend, Thenable
from .context import Context


@runtime_checkable
class _ThenableLike(Protocol):
    def then(self, cb: Any) -> Any: ...


def use(value: Any) -> Any:
    """
    Experimental `use()` surface (Phase 3).

    Minimal behavior:
    - ``Context`` values read like ``useContext``.
    - ``Thenable`` / `.then()` objects suspend while pending.
    - Otherwise return the value as-is.
    """
    if isinstance(value, Context):
        return value._get()
    if isinstance(value, Thenable):
        if value.status == "pending":
            raise Suspend(value)
        if value.status == "rejected":
            raise value.error
        return value.value
    if isinstance(value, _ThenableLike):
        status = getattr(value, "status", None)
        if status == "pending":
            raise Suspend(value)
        if status == "rejected":
            err = getattr(value, "error", None)
            raise err if isinstance(err, BaseException) else RuntimeError("rejected")
        if status == "fulfilled":
            return getattr(value, "value")
        raise Suspend(value)
    return value

