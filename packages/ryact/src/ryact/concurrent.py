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


# Profiler (noop-host driven initially)
Profiler = "__profiler__"


def profiler(*, id: str, on_render: Callable[..., Any], children: Any) -> Any:
    """
    Minimal Profiler wrapper (Phase 6).

    `on_render` matches the upstream callback shape loosely:
      on_render(id, phase, actual_duration, base_duration, start_time, commit_time, interactions)
    """
    from .element import create_element

    return create_element(
        Profiler,
        {
            "id": id,
            "on_render": on_render,
            "children": (children,),
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
_transition_tracing_callbacks: tuple[
    Callable[[str], None],
    Callable[[str], None],
] | None = None
_active_traced_transitions: set[str] = set()
_report_error: Callable[[BaseException], None] | None = None
_pending_async_actions: set[Thenable] = set()
_last_started_async_action: Thenable | None = None
_async_action_settled_listeners: list[Callable[[], None]] = []


def on_async_action_settled(cb: Callable[[], None]) -> Callable[[], None]:
    """
    Register a callback invoked whenever a pending async action settles.

    Minimal surface used by `useOptimistic` to schedule a rerender when an action finishes.
    """
    _async_action_settled_listeners.append(cb)

    def remove() -> None:
        try:
            _async_action_settled_listeners.remove(cb)
        except ValueError:
            pass

    return remove


def has_pending_async_actions() -> bool:
    return bool(_pending_async_actions)


def is_async_action_pending(action: Thenable | None) -> bool:
    if action is None:
        return False
    return action in _pending_async_actions


def current_async_action() -> Thenable | None:
    # Minimal heuristic used by useOptimistic: associate optimistic updates with the
    # latest started pending async action.
    return _last_started_async_action if _pending_async_actions else None


def set_report_error(fn: Callable[[BaseException], None] | None) -> None:
    """
    Minimal reportError surface used by translated async-actions tests.
    """
    global _report_error
    _report_error = fn


def set_transition_tracing_callbacks(
    *,
    on_transition_start: Callable[[str], None] | None = None,
    on_transition_complete: Callable[[str], None] | None = None,
) -> None:
    """
    Minimal transition tracing surface (Phase 13).

    When set, traced transitions started via ``start_transition(..., transition=Transition(...))``
    will emit deterministic start/complete callbacks.
    """
    global _transition_tracing_callbacks
    if on_transition_start is None or on_transition_complete is None:
        _transition_tracing_callbacks = None
        return
    _transition_tracing_callbacks = (on_transition_start, on_transition_complete)


def _notify_transition_lane_committed() -> None:
    cb = _transition_tracing_callbacks
    if cb is None:
        return
    if not _active_traced_transitions:
        return
    _on_start, on_complete = cb
    for name in sorted(_active_traced_transitions):
        on_complete(name)
    _active_traced_transitions.clear()


def start_transition(fn: Callable[[], Any], *, transition: Transition | None = None) -> Any:
    global _in_transition
    prev = _in_transition
    _in_transition = True
    try:
        cb = _transition_tracing_callbacks
        transition_name = transition.name if transition is not None else None
        if transition is not None and cb is not None:
            on_start, _on_complete = cb
            if transition.name not in _active_traced_transitions:
                _active_traced_transitions.add(transition.name)
                on_start(transition.name)
        _lane_stack.append(TRANSITION_LANE)
        try:
            result = fn()
        except BaseException as err:
            rep = _report_error
            if rep is not None:
                try:
                    rep(err)
                except Exception:
                    pass
            raise
        if isinstance(result, Thenable):
            rep = _report_error
            if result.status == "pending":
                _pending_async_actions.add(result)
                global _last_started_async_action
                _last_started_async_action = result

            def done() -> None:
                if result in _pending_async_actions:
                    _pending_async_actions.discard(result)
                # Transition tracing: complete when async action settles.
                if cb is not None and transition_name is not None:
                    _on_start2, on_complete2 = cb
                    try:
                        on_complete2(transition_name)
                    except Exception:
                        pass
                for cb2 in list(_async_action_settled_listeners):
                    try:
                        cb2()
                    except Exception:
                        pass
                if rep is None:
                    return
                if result.status == "rejected":
                    try:
                        rep(result.error)
                    except Exception:
                        pass

            result.then(done)
        else:
            # Transition tracing: sync transitions complete immediately.
            if cb is not None and transition_name is not None:
                _on_start2, on_complete2 = cb
                try:
                    on_complete2(transition_name)
                except Exception:
                    pass
        return result
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
