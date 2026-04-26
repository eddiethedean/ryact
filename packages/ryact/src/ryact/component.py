from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable, Mapping
from types import MappingProxyType
from typing import Any, Generic, TypeVar, cast

P = TypeVar("P", bound=Mapping[str, Any])


class Component(ABC, Generic[P]):
    """
    Optional class-based component (React class component shape).

    Props are passed as keyword arguments, matching ``create_element(Cls, {"a": 1})``
    and function components that receive ``**props``.
    """

    __slots__ = ("_props", "_state", "_schedule_update", "_pending_setstate_callbacks")

    def __init__(self, **props: Any) -> None:
        self._props = dict(props)
        self._state: dict[str, Any] = {}
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
        return MappingProxyType(self._state)

    # Minimal React-like state updates for class components (test-driven).
    def set_state(
        self,
        partial_state: Mapping[str, Any] | None = None,
        *,
        callback: Callable[[], None] | None = None,
    ) -> None:
        if partial_state is not None:
            self._state.update(dict(partial_state))
        if callback is not None:
            self._pending_setstate_callbacks.append(callback)
        if self._schedule_update is not None:
            self._schedule_update()

    # Alias for React familiarity.
    def setState(
        self,
        partial_state: Mapping[str, Any] | None = None,
        callback: Callable[[], None] | None = None,
    ) -> None:
        self.set_state(partial_state, callback=callback)

    @abstractmethod
    def render(self) -> Any:
        """Return an element tree (same renderables as function components)."""
        ...
