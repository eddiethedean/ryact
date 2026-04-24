from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from .reconciler import TRANSITION_LANE, Lane


@dataclass
class Suspense:
    fallback: Any
    children: Any


@dataclass
class Transition:
    name: str = "default"


class Thenable:
    def __init__(self) -> None:
        self._callbacks: list[Callable[[], None]] = []
        self._resolved = False

    def then(self, cb: Callable[[], None]) -> None:
        if self._resolved:
            cb()
            return
        self._callbacks.append(cb)

    def resolve(self) -> None:
        if self._resolved:
            return
        self._resolved = True
        callbacks = list(self._callbacks)
        self._callbacks.clear()
        for cb in callbacks:
            cb()


class Suspend(Exception):
    def __init__(self, thenable: Thenable) -> None:
        super().__init__("Suspended")
        self.thenable = thenable


def suspense(*, fallback: Any, children: Any) -> Any:
    # Represent Suspense boundaries as a special host type to avoid circular imports
    # in the reconciler.
    from .element import create_element

    return create_element("__suspense__", {"fallback": fallback, "children": (children,)})


# StrictMode is represented as a special host type for the noop reconciler.
StrictMode = "__strict_mode__"


def strict_mode(children: Any) -> Any:
    from .element import create_element

    return create_element(StrictMode, {"children": (children,)})


# Portals (host-owned; minimal representation in core)
Portal = "__portal__"


def create_portal(*, children: Any, container: Any) -> Any:
    from .element import create_element

    return create_element(Portal, {"children": (children,), "container": container})


_in_transition = False
_lane_stack: list[Lane] = []


def start_transition(fn: Callable[[], None]) -> None:
    global _in_transition
    prev = _in_transition
    _in_transition = True
    try:
        _lane_stack.append(TRANSITION_LANE)
        fn()
    finally:
        _lane_stack.pop()
        _in_transition = prev


def is_in_transition() -> bool:
    return _in_transition


def current_update_lane() -> Lane | None:
    if not _lane_stack:
        return None
    return _lane_stack[-1]


class Lazy:
    def __init__(self, loader: Callable[[], Any]) -> None:
        self._loader = loader
        self._resolved = False
        self._value: Any | None = None

    def get(self) -> Any:
        if not self._resolved:
            self._value = self._loader()
            self._resolved = True
        return self._value


class LazyComponent:
    def __init__(self, loader: Callable[[], Any]) -> None:
        self._lazy = Lazy(loader)

    def __call__(self, **props: Any) -> Any:
        value = self._lazy.get()
        # Support either a component type or an already-created element.
        from .element import Element, create_element

        if isinstance(value, Element):
            return value
        if callable(value):
            return create_element(value, props)
        raise TypeError(f"Unsupported lazy resolved value: {type(value)!r}")


def lazy(loader: Callable[[], Any]) -> LazyComponent:
    return LazyComponent(loader)
