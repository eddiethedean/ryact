"""DEV warnings and root registry (ReactDOMRoot / createRoot parity)."""
from __future__ import annotations

import warnings
from typing import Any

from ryact.dev import is_dev

from .dom import Container

_warned_duplicate_create_root: set[int] = set()
_container_active_root: dict[int, Any] = {}


def reset_root_dev_state() -> None:
    _warned_duplicate_create_root.clear()
    _container_active_root.clear()


def register_root_for_container(container: Container, root: Any) -> None:
    cid = id(container)
    if cid in _container_active_root and is_dev() and cid not in _warned_duplicate_create_root:
        _warned_duplicate_create_root.add(cid)
        warnings.warn(
            "You are calling ReactDOMClient.createRoot() on a container that has already been "
            "passed to createRoot() before. Instead, call root.render() on the existing root "
            "instead if you want to update it.",
            UserWarning,
            stacklevel=3,
        )
    _container_active_root[cid] = root


def unregister_root_for_container(container: Container) -> None:
    cid = id(container)
    _container_active_root.pop(cid, None)
    _warned_duplicate_create_root.discard(cid)


def warn_render_extra_callback() -> None:
    if not is_dev():
        return
    warnings.warn(
        "does not support the second callback argument. To execute a side effect after "
        "rendering, declare it in a component body with useEffect().",
        UserWarning,
        stacklevel=3,
    )


def warn_render_extra_argument(kind: str) -> None:
    if not is_dev():
        return
    if kind == "object":
        warnings.warn(
            "You passed a second argument to root.render(...) but it only accepts one argument.",
            UserWarning,
            stacklevel=3,
        )
    elif kind == "container":
        warnings.warn(
            "You passed a container to the second argument of root.render(...). You don't need "
            "to pass it again since you already passed it to create the root.",
            UserWarning,
            stacklevel=3,
        )


def warn_unmount_extra_callback() -> None:
    if not is_dev():
        return
    warnings.warn(
        "does not support a callback argument. To execute a side effect after rendering, "
        "declare it in a component body with useEffect().",
        UserWarning,
        stacklevel=3,
    )


def warn_hydrate_root_missing_children() -> None:
    if not is_dev():
        return
    warnings.warn(
        "Must provide initial children as second argument to hydrateRoot. "
        "Example usage: hydrateRoot(domContainer, <App />)",
        UserWarning,
        stacklevel=3,
    )


def warn_create_root_on_document_body() -> None:
    if not is_dev():
        return
    warnings.warn(
        "createRoot(): Creating roots directly on document.body is discouraged, "
        "since its children are often manipulated by third-party scripts.",
        UserWarning,
        stacklevel=3,
    )


def warn_create_root_jsx_element() -> None:
    if not is_dev():
        return
    warnings.warn(
        "You passed a JSX element to createRoot. You probably meant to call root.render instead. "
        "Example usage:\n\n"
        "  let root = createRoot(domContainer);\n"
        "  root.render(<App />);",
        UserWarning,
        stacklevel=3,
    )


def warn_render_invalid_child(kind: str, *, detail: str = "") -> None:
    if not is_dev():
        return
    if kind == "function":
        warnings.warn(
            "Functions are not valid as a React child. This may happen if you return "
            f"Component instead of <Component /> from render. Or maybe you meant to call "
            f"this function rather than return it.{detail}",
            UserWarning,
            stacklevel=3,
        )
    elif kind == "symbol":
        warnings.warn(
            f"Symbols are not valid as a React child.{detail}",
            UserWarning,
            stacklevel=3,
        )
