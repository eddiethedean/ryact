from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any, Generic, TypeVar, cast

T = TypeVar("T")

_UNSET: object = object()

_current_context_consumer: Any | None = None
_context_provider_stacks: ContextVar[dict[int, list[Any]] | None] = ContextVar(
    "ryact_context_provider_stacks", default=None
)


def _provider_stacks() -> dict[int, list[Any]]:
    stacks = _context_provider_stacks.get()
    if stacks is None:
        stacks = {}
        _context_provider_stacks.set(stacks)
    return stacks


def reset_context_provider_stacks() -> None:
    _context_provider_stacks.set({})


@contextmanager
def _with_context_provider(context: Context[Any], value: Any) -> Iterator[None]:
    stacks = _provider_stacks()
    cid = id(context)
    stack = stacks.setdefault(cid, [])
    stack.append(value)
    try:
        yield
    finally:
        stack.pop()
        if not stack:
            del stacks[cid]


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
    _current_value: T | object = _UNSET

    @property
    def Provider(self) -> Context[T]:
        """React parity: ``Context.Provider`` is the context object itself."""

        return self

    def _get(self) -> T:
        stacks = _context_provider_stacks.get()
        stack = stacks.get(id(self)) if stacks is not None else None
        value = (
            stack[-1] if stack else self.default_value if self._current_value is _UNSET else self._current_value  # type: ignore[assignment]
        )
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
        return cast(T, value)

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


def context_provider(context: Context[Any], value: Any, child: Any) -> Any:
    """Test/reconciler hook: render `child` with Context._current_value set to `value`."""
    from .element import create_element

    return create_element(
        "__context_provider__",
        {"context": context, "value": value, "children": (child,) if child is not None else ()},
    )


def _provider(context: Context[T], value: T, children: Any) -> Any:
    with _with_context_provider(context, value):
        return children


def _consumer(context: Context[T], render: Callable[[T], Any]) -> Any:
    return render(context._get())
