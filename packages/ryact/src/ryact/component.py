from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable, Mapping
from contextlib import suppress
from types import MappingProxyType
from typing import Any, Generic, TypeVar, cast

import warnings

from .act import is_act_environment_enabled, is_in_act_scope

P = TypeVar("P", bound=Mapping[str, Any])


class Component(ABC, Generic[P]):
    """
    Optional class-based component (React class component shape).

    Props are passed as keyword arguments, matching ``create_element(Cls, {"a": 1})``
    and function components that receive ``**props``.
    """

    __slots__ = ("_props", "_state", "_schedule_update", "_pending_setstate_callbacks", "refs")

    _shared_empty_refs: Mapping[str, Any] = MappingProxyType({})

    def __init__(self, **props: Any) -> None:
        self._props = dict(props)
        self._state: dict[str, Any] = {}
        # React class components expose `this.refs` (legacy string refs). Even when unused,
        # it's a frozen shared empty object.
        self.refs = Component._shared_empty_refs
        # Filled by the renderer (noop/DOM/etc) during render so class components can
        # request an update. The exact scheduling semantics are renderer-owned.
        self._schedule_update: Callable[[], None] | None = None
        self._pending_setstate_callbacks: list[Callable[[], None]] = []

    @property
    def props(self) -> P:
        """Read-only props (React props are effectively immutable during render)."""
        return cast(P, MappingProxyType(self._props))

    @property
    def state(self) -> Mapping[str, Any]:
        """Read-only state mapping (minimal, expanded only as tests demand)."""
        if not isinstance(self._state, dict):
            # Some upstream warnings cover invalid `this.state` initial values; keep the
            # public view safe even if user code mutates the private slot.
            return MappingProxyType({})
        return MappingProxyType(self._state)

    # Minimal React-like state updates for class components (test-driven).
    def set_state(
        self,
        partial_state: Mapping[str, Any]
        | Callable[[Mapping[str, Any], Mapping[str, Any]], Mapping[str, Any] | None]
        | None = None,
        *,
        callback: Callable[[], None] | None = None,
    ) -> None:
        if is_act_environment_enabled() and not is_in_act_scope():
            warnings.warn(
                "An update to a class component was not wrapped in act(...).",
                category=RuntimeWarning,
                stacklevel=2,
            )
        # Upstream: setState is queued; reading `this.state` in the same tick
        # returns the previous value until React flushes.
        if partial_state is not None:
            from .concurrent import current_update_lane
            from .hooks import _current_commit_phase
            from .reconciler import DEFAULT_LANE, SYNC_LANE, Lane

            lane: Lane = current_update_lane() or (
                SYNC_LANE if _current_commit_phase is not None else DEFAULT_LANE
            )
            pending = getattr(self, "_pending_state_updates", None)
            if pending is None:
                pending = []
                self._pending_state_updates = pending  # type: ignore[attr-defined]
            if callable(partial_state):
                pending.append((lane, partial_state, False))
            else:
                pending.append((lane, dict(partial_state), False))
        if callback is not None:
            self._pending_setstate_callbacks.append(callback)
        if self._schedule_update is not None:
            # Upstream: errors thrown while scheduling an update should not prevent
            # already-enqueued state updates (or sibling updates in the same batch)
            # from being applied on a later flush.
            with suppress(Exception):
                self._schedule_update()

    def replace_state(
        self,
        state: Mapping[str, Any]
        | Callable[[Mapping[str, Any], Mapping[str, Any]], Mapping[str, Any] | None]
        | None = None,
        *,
        callback: Callable[[], None] | None = None,
    ) -> None:
        if is_act_environment_enabled() and not is_in_act_scope():
            warnings.warn(
                "An update to a class component was not wrapped in act(...).",
                category=RuntimeWarning,
                stacklevel=2,
            )
        if state is not None:
            from .concurrent import current_update_lane
            from .hooks import _current_commit_phase
            from .reconciler import DEFAULT_LANE, SYNC_LANE, Lane

            lane: Lane = current_update_lane() or (
                SYNC_LANE if _current_commit_phase is not None else DEFAULT_LANE
            )
            pending = getattr(self, "_pending_state_updates", None)
            if pending is None:
                pending = []
                self._pending_state_updates = pending  # type: ignore[attr-defined]
            else:
                # Upstream: replaceState "resets" the queue at its priority, dropping
                # any queued updates with equal or lesser priority.
                #
                # For our simplified model (pending updates live on the instance),
                # trim the queue to retain only higher-priority work.
                pending[:] = [
                    item
                    for item in pending
                    if isinstance(item, tuple)
                    and len(item) == 3
                    and isinstance(item[0], Lane)
                    and item[0].priority < lane.priority
                ]
            if callable(state):
                pending.append((lane, state, True))
            else:
                pending.append((lane, dict(state), True))
        if callback is not None:
            self._pending_setstate_callbacks.append(callback)
        if self._schedule_update is not None:
            with suppress(Exception):
                self._schedule_update()

    # Alias for React familiarity.
    def setState(
        self,
        partial_state: Mapping[str, Any]
        | Callable[[Mapping[str, Any], Mapping[str, Any]], Mapping[str, Any] | None]
        | None = None,
        callback: Callable[[], None] | None = None,
    ) -> None:
        self.set_state(partial_state, callback=callback)

    def replaceState(
        self,
        state: Mapping[str, Any]
        | Callable[[Mapping[str, Any], Mapping[str, Any]], Mapping[str, Any] | None]
        | None = None,
        callback: Callable[[], None] | None = None,
    ) -> None:
        self.replace_state(state, callback=callback)

    def force_update(self, callback: Callable[[], None] | None = None) -> None:
        if is_act_environment_enabled() and not is_in_act_scope():
            warnings.warn(
                "An update to a class component was not wrapped in act(...).",
                category=RuntimeWarning,
                stacklevel=2,
            )
        if callback is not None:
            self._pending_setstate_callbacks.append(callback)
        # Used by the reconciler to bypass shouldComponentUpdate bailouts.
        try:
            self._force_update = True  # type: ignore[attr-defined]
        except Exception:
            pass
        if self._schedule_update is not None:
            with suppress(Exception):
                self._schedule_update()

    def forceUpdate(self, callback: Callable[[], None] | None = None) -> None:
        self.force_update(callback)

    def __getattr__(self, name: str) -> Any:
        # Classic React class APIs are intentionally not supported; DEV should warn.
        if name in ("isMounted", "replaceProps"):
            from .dev import is_dev

            if is_dev():
                warnings.warn(
                    f"Attempted to access classic API `{name}` on an ES6 class component.",
                    RuntimeWarning,
                    stacklevel=2,
                )
            raise AttributeError(name)
        raise AttributeError(name)

    @abstractmethod
    def render(self) -> Any:
        """Return an element tree (same renderables as function components)."""
        ...


def _shallow_equal(a: Mapping[str, Any], b: Mapping[str, Any]) -> bool:
    if a.keys() != b.keys():
        return False
    for k, av in a.items():
        if av != b.get(k):
            return False
    return True


class PureComponent(Component[P]):
    """
    React.PureComponent-like base class.

    Uses shallow equality for props/state to determine shouldComponentUpdate.
    """

    def shouldComponentUpdate(self, nextProps: Mapping[str, Any], nextState: Mapping[str, Any]) -> bool:  # noqa: N802
        return (not _shallow_equal(self.props, nextProps)) or (not _shallow_equal(self.state, nextState))
