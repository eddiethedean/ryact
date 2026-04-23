from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from types import MappingProxyType
from typing import Any


class Component(ABC):
    """
    Optional class-based component (React class component shape).

    Props are passed as keyword arguments, matching ``create_element(Cls, {"a": 1})``
    and function components that receive ``**props``.
    """

    __slots__ = ("_props",)

    def __init__(self, **props: Any) -> None:
        self._props = dict(props)

    @property
    def props(self) -> Mapping[str, Any]:
        """Read-only props (React props are effectively immutable during render)."""
        return MappingProxyType(self._props)

    @abstractmethod
    def render(self) -> Any:
        """Return an element tree (same renderables as function components)."""
        ...
