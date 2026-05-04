from __future__ import annotations

import warnings
from typing import Any, Protocol, runtime_checkable

from .concurrent import Suspend, Thenable
from .context import Context


@runtime_checkable
class _ThenableLike(Protocol):
    def then(self, cb: Any) -> Any: ...


def _warn_uncached_thenable_read() -> None:
    """DEV: `use()` on a thenable that is not :class:`Thenable` (upstream uncached promise)."""
    try:
        from .dev import is_dev

        if not is_dev():
            return
    except Exception:
        return
    warnings.warn(
        "A component was suspended by an uncached promise. Creating ad-hoc thenables inside "
        "a component without ryact.concurrent.Thenable (or a cache integration) is not yet "
        "supported in ryact.",
        RuntimeWarning,
        stacklevel=3,
    )


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
            # If userland catches the suspension, hooks must already be disabled.
            try:
                from .hooks import _mark_current_frame_suspended

                _mark_current_frame_suspended()
            except Exception:
                pass
            raise Suspend(value)
        if value.status == "rejected":
            raise value.error
        return value.value
    if isinstance(value, _ThenableLike):
        _warn_uncached_thenable_read()
        status = getattr(value, "status", None)
        if status == "pending":
            try:
                from .hooks import _mark_current_frame_suspended

                _mark_current_frame_suspended()
            except Exception:
                pass
            raise Suspend(value)
        if status == "rejected":
            err = getattr(value, "error", None)
            raise err if isinstance(err, BaseException) else RuntimeError("rejected")
        if status == "fulfilled":
            return value.value
        try:
            from .hooks import _mark_current_frame_suspended

            _mark_current_frame_suspended()
        except Exception:
            pass
        raise Suspend(value)
    return value
