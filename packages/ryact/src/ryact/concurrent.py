from __future__ import annotations

from collections.abc import Callable
from contextlib import contextmanager
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
        self._status: str = "pending"  # pending | fulfilled | rejected
        self._value: Any = None
        self._error: BaseException | None = None

    def then(self, cb: Callable[[], None]) -> None:
        if self._status != "pending":
            cb()
            return
        self._callbacks.append(cb)

    @property
    def status(self) -> str:
        return self._status

    @property
    def value(self) -> Any:
        if self._status != "fulfilled":
            raise RuntimeError("Thenable value is only available when fulfilled")
        return self._value

    @property
    def error(self) -> BaseException:
        if self._status != "rejected" or self._error is None:
            raise RuntimeError("Thenable error is only available when rejected")
        return self._error

    def resolve(self, value: Any = None) -> None:
        if self._status != "pending":
            return
        self._status = "fulfilled"
        self._value = value
        callbacks = list(self._callbacks)
        self._callbacks.clear()
        for cb in callbacks:
            cb()

    def reject(self, err: BaseException) -> None:
        if self._status != "pending":
            return
        self._status = "rejected"
        self._error = err
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


# Fragments (wrapper type; transparent in host output)
Fragment = "__fragment__"


def fragment(*children: Any) -> Any:
    from .element import create_element

    return create_element(Fragment, {"children": children})


# SuspenseList (noop-host driven initially)
SuspenseList = "__suspense_list__"


def suspense_list(
    *,
    children: Any,
    reveal_order: str | None = None,
    tail: str | None = None,
) -> Any:
    """
    Minimal SuspenseList representation (Phase 4).

    `reveal_order`: "forwards" | "backwards" | "together" (default: "forwards")
    `tail`: "hidden" | "collapsed" (default: "hidden")
    """
    from .element import create_element

    return create_element(
        SuspenseList,
        {
            "children": (children,),
            "reveal_order": reveal_order,
            "tail": tail,
        },
    )


# Offscreen/Activity (visibility wrapper; noop-host driven initially)
Offscreen = "__offscreen__"


def offscreen(*, children: Any, mode: str = "visible") -> Any:
    """
    Minimal Offscreen/Activity-like wrapper.

    `mode` is currently either \"visible\" or \"hidden\" and is interpreted by the
    noop reconciler/renderer path only (expanded by translated tests).
    """
    from .element import create_element

    return create_element(Offscreen, {"mode": mode, "children": (children,)})


# Convenience alias used by translated tests (upstream calls this Activity/Offscreen).
Activity = Offscreen


def activity(*, children: Any, mode: str = "visible", hidden: bool | None = None) -> Any:
    # Upstream has had multiple experimental prop shapes here; for now we accept
    # `hidden=` as an alias for `mode='hidden'` and let the renderer emit a DEV warning
    # with component stack context during render.
    warn_hidden = hidden is not None
    if hidden is not None and hidden:
        mode = "hidden"
    from .element import create_element

    return create_element(
        Offscreen, {"mode": mode, "children": (children,), "__warn_hidden__": warn_hidden}
    )


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


@contextmanager
def _with_update_lane(lane: Lane) -> Any:
    _lane_stack.append(lane)
    try:
        yield
    finally:
        _lane_stack.pop()


class Lazy:
    def __init__(self, loader: Callable[[], Any]) -> None:
        self._loader = loader
        self._status: str = "uninitialized"  # uninitialized | pending | fulfilled | rejected
        self._value: Any | None = None
        self._error: BaseException | None = None
        self._thenable: Thenable | None = None

    def _resolve_value(self, v: Any) -> Any:
        # Upstream React.lazy expects a module object with a `default` export.
        # For compatibility with earlier ryact slices, we also accept component types
        # or already-created elements.
        if isinstance(v, dict) and "default" in v:
            return v["default"]
        return v

    def get(self) -> Any:
        from .concurrent import Suspend  # avoid cycle in older tooling

        if self._status == "fulfilled":
            return self._value
        if self._status == "rejected":
            assert self._error is not None
            raise self._error
        if self._status == "pending":
            assert self._thenable is not None
            # If the thenable has since settled, adopt its outcome.
            if self._thenable.status == "fulfilled":
                self._value = self._resolve_value(self._thenable.value)
                self._status = "fulfilled"
                self._thenable = None
                return self._value
            if self._thenable.status == "rejected":
                self._error = self._thenable.error
                self._status = "rejected"
                self._thenable = None
                raise self._error
            raise Suspend(self._thenable)

        # First attempt: call loader
        try:
            v = self._loader()
        except BaseException as err:
            self._error = err
            self._status = "rejected"
            raise

        if isinstance(v, Thenable):
            if v.status == "fulfilled":
                self._value = self._resolve_value(v.value)
                self._status = "fulfilled"
                return self._value
            if v.status == "rejected":
                self._error = v.error
                self._status = "rejected"
                raise self._error
            self._thenable = v
            self._status = "pending"
            raise Suspend(v)

        self._value = self._resolve_value(v)
        self._status = "fulfilled"
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
