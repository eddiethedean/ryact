"""Host and class-instance ref attach/detach (refs-test parity)."""

from __future__ import annotations

import contextlib
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
        except BaseException as err:
            container = getattr(node, "_event_container", None)
            boundary = getattr(node, "_ryact_dom_error_boundary", None)
            if container is not None and boundary is not None:
                from .root import _dom_catch_on_boundary

                if _dom_catch_on_boundary(
                    container,
                    boundary,
                    err,
                    prefer_first_captured_error=False,
                ):
                    return
                else:
                    from .error_reporting import report_uncaught_error

                    report_uncaught_error(container, err)
            else:
                raise err
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
        container = getattr(node, "_event_container", None)
        if container is not None:
            container._ryact_dom_in_ref_attach = True  # type: ignore[attr-defined]
            container._ryact_dom_ref_attach_updates = 0  # type: ignore[attr-defined]
            container._ryact_dom_ref_attach_aborted = False  # type: ignore[attr-defined]
        try:
            try:
                result = ref(node)
            except RuntimeError as err:
                if "Maximum update depth exceeded" in str(err):
                    from .error_reporting import report_uncaught_error

                    if container is not None:
                        report_uncaught_error(container, err)
                    return
                raise
            if callable(result):
                node._host_ref_cleanup = result  # type: ignore[attr-defined]
        except BaseException as err:
            container = getattr(node, "_event_container", None)
            if container is not None:
                from .error_reporting import report_uncaught_error

                report_uncaught_error(container, err)
            else:
                raise
        finally:
            if container is not None:
                container._ryact_dom_in_ref_attach = False  # type: ignore[attr-defined]
    elif hasattr(ref, "current"):
        try:
            ref.current = node
        except BaseException as err:
            container = getattr(node, "_event_container", None)
            if container is not None:
                from .error_reporting import report_uncaught_error

                report_uncaught_error(container, err)
            else:
                raise
    else:
        _warn_invalid_ref(msg="Invalid ref object provided; expected a callable ref or an object with `current`.")
        return
    node._host_ref_attached = ref  # type: ignore[attr-defined]


def attach_component_ref(instance: Any, ref: Any | None) -> None:
    """Attach ``ref`` to a class component instance (React class / forward ref subset)."""

    from .dom_internals import mark_class_component_committed

    mark_class_component_committed(instance)
    if ref is not None:
        instance._ryact_last_comp_ref = ref  # type: ignore[attr-defined]
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
            _warn_invalid_ref(msg=("Function components cannot have string refs. We recommend using useRef() instead."))
        else:
            _warn_invalid_ref(msg="Invalid ref object provided; expected a callable ref or an object with `current`.")
    except Exception:
        pass


def detach_component_ref(instance: Any, ref: Any | None) -> None:
    if ref is None:
        return
    cleanup = getattr(instance, "_ryact_ref_cleanup", None)
    if callable(cleanup):
        with contextlib.suppress(Exception):
            cleanup()
    try:
        if callable(ref):
            ref(None)
        elif hasattr(ref, "current"):
            ref.current = None
    except Exception:
        pass
