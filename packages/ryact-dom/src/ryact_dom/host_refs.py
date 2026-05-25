"""Host and class-instance ref attach/detach (refs-test parity)."""

from __future__ import annotations

import warnings
from typing import Any

from ryact.dev import is_dev

from .dom import ElementNode


def _warn_invalid_ref(*, msg: str) -> None:
    if is_dev():
        warnings.warn(msg, RuntimeWarning, stacklevel=4)


def detach_host_ref(node: ElementNode) -> None:
    ref = getattr(node, "_host_ref_attached", None)
    if ref is None:
        return
    cleanup = getattr(node, "_host_ref_cleanup", None)
    if callable(cleanup):
        try:
            cleanup()
        except Exception:
            pass
        node._host_ref_cleanup = None  # type: ignore[attr-defined]
    try:
        if callable(ref):
            ref(None)
        elif hasattr(ref, "current"):
            ref.current = None
    except Exception:
        pass
    node._host_ref_attached = None  # type: ignore[attr-defined]


def commit_host_ref(node: ElementNode, ref: Any | None) -> None:
    """Attach ``ref`` to a committed host ``ElementNode`` (or detach when ``ref`` is None)."""

    prev = getattr(node, "_host_ref_attached", None)
    if ref is prev and ref is not None:
        return
    detach_host_ref(node)
    if ref is None:
        return
    if isinstance(ref, str):
        _warn_invalid_ref(
            msg=(
                "Function components cannot have string refs. "
                "We recommend using useRef() instead. "
                "Learn more about using refs safely here: "
                "https://react.dev/link/strict-mode-string-ref"
            )
        )
        return
    if callable(ref):
        try:
            result = ref(node)
            if callable(result):
                node._host_ref_cleanup = result  # type: ignore[attr-defined]
        except Exception:
            pass
    elif hasattr(ref, "current"):
        try:
            ref.current = node
        except Exception:
            pass
    else:
        _warn_invalid_ref(
            msg="Invalid ref object provided; expected a callable ref or an object with `current`."
        )
        return
    node._host_ref_attached = ref  # type: ignore[attr-defined]


def attach_component_ref(instance: Any, ref: Any | None) -> None:
    """Attach ``ref`` to a class component instance (React class / forward ref subset)."""

    if ref is None:
        return
    try:
        if callable(ref):
            result = ref(instance)
            if callable(result):
                # Store cleanup on instance for unmount parity (minimal).
                instance._ryact_ref_cleanup = result
        elif hasattr(ref, "current"):
            ref.current = instance
        elif isinstance(ref, str):
            _warn_invalid_ref(
                msg=(
                    "Function components cannot have string refs. "
                    "We recommend using useRef() instead."
                )
            )
        else:
            _warn_invalid_ref(msg="Invalid ref object provided; expected a callable ref or an object with `current`.")
    except Exception:
        pass


def detach_component_ref(instance: Any, ref: Any | None) -> None:
    if ref is None:
        return
    cleanup = getattr(instance, "_ryact_ref_cleanup", None)
    if callable(cleanup):
        try:
            cleanup()
        except Exception:
            pass
    try:
        if callable(ref):
            ref(None)
        elif hasattr(ref, "current"):
            ref.current = None
    except Exception:
        pass
