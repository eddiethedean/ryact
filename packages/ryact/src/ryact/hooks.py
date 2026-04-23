from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, TypeVar

from .component import Component

S = TypeVar("S")
A = TypeVar("A")
R = TypeVar("R")


class HookError(RuntimeError):
    pass


@dataclass
class _HookFrame:
    hook_index: int
    hooks: list[Any]


_current_frame = None  # type: Optional[_HookFrame]


def _push_frame(hooks: list[Any]) -> None:
    global _current_frame
    if _current_frame is not None:
        raise HookError("Nested hook frames are not supported yet.")
    _current_frame = _HookFrame(hook_index=0, hooks=hooks)


def _pop_frame() -> None:
    global _current_frame
    _current_frame = None


def _next_slot() -> tuple[_HookFrame, int]:
    if _current_frame is None:
        raise HookError("Hooks can only be used while rendering a component.")
    idx = _current_frame.hook_index
    _current_frame.hook_index += 1
    return _current_frame, idx


def use_state(initial: S) -> tuple[S, Callable[[S], None]]:
    frame, idx = _next_slot()
    if idx >= len(frame.hooks):
        frame.hooks.append(initial)

    def set_state(next_value: S) -> None:
        frame.hooks[idx] = next_value

    return frame.hooks[idx], set_state  # type: ignore[return-value]


def use_reducer(reducer: Callable[[S, A], S], initial: S) -> tuple[S, Callable[[A], None]]:
    frame, idx = _next_slot()
    if idx >= len(frame.hooks):
        frame.hooks.append(initial)

    def dispatch(action: A) -> None:
        frame.hooks[idx] = reducer(frame.hooks[idx], action)

    return frame.hooks[idx], dispatch  # type: ignore[return-value]


def use_ref(initial: Any = None) -> dict[str, Any]:
    frame, idx = _next_slot()
    if idx >= len(frame.hooks):
        frame.hooks.append({"current": initial})
    return frame.hooks[idx]


def use_memo(factory: Callable[[], R], deps: tuple[Any, ...] | None = None) -> R:
    frame, idx = _next_slot()
    if idx >= len(frame.hooks):
        value = factory()
        frame.hooks.append((value, deps))
        return value
    value, old_deps = frame.hooks[idx]
    if deps is None or old_deps is None or deps != old_deps:
        value = factory()
        frame.hooks[idx] = (value, deps)
    return value


def use_callback(fn: Callable[..., Any], deps: tuple[Any, ...] | None = None) -> Callable[..., Any]:
    return use_memo(lambda: fn, deps)


def use_effect(
    effect: Callable[[], Callable[[], None] | None], deps: tuple[Any, ...] | None = None
) -> None:
    # Placeholder: effect scheduling handled by reconciler later.
    frame, idx = _next_slot()
    if idx >= len(frame.hooks):
        cleanup = effect()
        frame.hooks.append((cleanup, deps))
        return
    cleanup, old_deps = frame.hooks[idx]
    if deps is None or old_deps is None or deps != old_deps:
        if cleanup is not None:
            cleanup()
        cleanup = effect()
        frame.hooks[idx] = (cleanup, deps)


def use_layout_effect(
    effect: Callable[[], Callable[[], None] | None], deps: tuple[Any, ...] | None = None
) -> None:
    # Placeholder: same behavior as use_effect for now.
    use_effect(effect, deps)


def _is_class_component(component_type: Any) -> bool:
    if not isinstance(component_type, type):
        return False
    try:
        return issubclass(component_type, Component)
    except TypeError:
        return False


# Used by renderers to establish hook context.
def _render_with_hooks(fn: Callable[..., Any], props: dict[str, Any], hooks: list[Any]) -> Any:
    _push_frame(hooks)
    try:
        return fn(**props)
    finally:
        _pop_frame()


def _render_component(component_type: Any, props: dict[str, Any], hooks: list[Any]) -> Any:
    if _is_class_component(component_type):
        instance = component_type(**props)

        def _call_render(**_: Any) -> Any:
            return instance.render()

        return _render_with_hooks(_call_render, {}, hooks)
    if isinstance(component_type, type):
        raise TypeError(
            "Expected a function component or a subclass of Component, "
            f"got class {component_type!r}"
        )
    if callable(component_type):
        return _render_with_hooks(component_type, props, hooks)
    raise TypeError(f"Unsupported component type: {component_type!r}")
