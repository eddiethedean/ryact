from __future__ import annotations

from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Generic, TypeVar

T = TypeVar("T")

_current_context_consumer: Any | None = None


@contextmanager
def _with_current_context_consumer(fiber: Any) -> Any:
    global _current_context_consumer
    prev = _current_context_consumer
    _current_context_consumer = fiber
    try:
        yield
    finally:
        _current_context_consumer = prev


@dataclass
class Context(Generic[T]):
    default_value: T
    _current_value: T | None = None

    def _get(self) -> T:
        value = self._current_value if self._current_value is not None else self.default_value
        fiber = _current_context_consumer
        if fiber is not None:
            deps = getattr(fiber, "_context_deps", None)
            if not isinstance(deps, dict):
                deps = {}
                try:
                    fiber._context_deps = deps  # type: ignore[attr-defined]
                except Exception:
                    deps = None
            if isinstance(deps, dict):
                deps[id(self)] = (self, value)
        return value

    @property
    def Consumer(self) -> ContextConsumerMarker[T]:
        return ContextConsumerMarker(context=self)


@dataclass(frozen=True)
class ContextConsumerMarker(Generic[T]):
    """``create_element(ctx.Consumer, None, fn)`` render-prop consumer.

    Prefer ``use_context(ctx)`` (or ``use(ctx)``) inside function components; ``Consumer`` mirrors
    JSX-style ``<Ctx.Consumer>{value => ...}</>`` parity.
    """

    context: Context[T]


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
