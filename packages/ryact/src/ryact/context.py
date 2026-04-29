from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Generic, TypeVar

T = TypeVar("T")


@dataclass
class Context(Generic[T]):
    default_value: T
    _current_value: T | None = None

    def _get(self) -> T:
        return self._current_value if self._current_value is not None else self.default_value


def create_context(default_value: T) -> Context[T]:
    return Context(default_value=default_value)


def context_provider(context: Context[T], value: T, child: Any) -> Any:
    """Test/reconciler hook: render `child` with Context._current_value set to `value`."""
    from .element import create_element

    return create_element(
        "__context_provider__",
        {"context": context, "value": value, "children": (child,) if child is not None else ()},
    )


def _provider(context: Context[T], value: T, children: Any) -> Any:
    prev = context._current_value
    context._current_value = value
    try:
        return children
    finally:
        context._current_value = prev


def _consumer(context: Context[T], render: Callable[[T], Any]) -> Any:
    return render(context._get())
