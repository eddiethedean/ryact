from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Optional, TypeVar

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
    scheduled_layout_effects: list[Callable[[], None]]
    scheduled_passive_effects: list[Callable[[], None]]
    schedule_update: Callable[[Any], None] | None
    default_lane: Any | None


_current_frame: Optional[_HookFrame] = None


@dataclass
class _PendingUpdate:
    lane: Any
    value: Any


@dataclass
class _StateHook:
    value: Any
    pending: list[_PendingUpdate]


def _lane_priority(lane: Any) -> int:
    try:
        return int(lane.priority)
    except Exception:
        return 0


def _push_frame(
    hooks: list[Any],
    *,
    scheduled_layout_effects: list[Callable[[], None]] | None = None,
    scheduled_passive_effects: list[Callable[[], None]] | None = None,
    schedule_update: Callable[[Any], None] | None = None,
    default_lane: Any | None = None,
) -> None:
    global _current_frame
    if _current_frame is not None:
        raise HookError("Nested hook frames are not supported yet.")
    _current_frame = _HookFrame(
        hook_index=0,
        hooks=hooks,
        scheduled_layout_effects=scheduled_layout_effects
        if scheduled_layout_effects is not None
        else [],
        scheduled_passive_effects=scheduled_passive_effects
        if scheduled_passive_effects is not None
        else [],
        schedule_update=schedule_update,
        default_lane=default_lane,
    )


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
        frame.hooks.append(_StateHook(value=initial, pending=[]))

    slot = frame.hooks[idx]
    if not isinstance(slot, _StateHook):
        raise HookError("Hook order/type mismatch for use_state.")

    # Apply pending updates visible at this render lane.
    if frame.default_lane is not None and slot.pending:
        visible_pri = _lane_priority(frame.default_lane)
        remaining: list[_PendingUpdate] = []
        for upd in slot.pending:
            if _lane_priority(upd.lane) <= visible_pri:
                slot.value = upd.value
            else:
                remaining.append(upd)
        slot.pending = remaining

    def set_state(next_value: S) -> None:
        if frame.schedule_update is None:
            # Non-reconciler renderers (DOM/native) still use an eager model.
            slot.value = next_value
            return
        from .concurrent import current_update_lane

        lane = current_update_lane() or frame.default_lane
        slot.pending.append(_PendingUpdate(lane=lane, value=next_value))
        frame.schedule_update(lane)

    return slot.value, set_state  # type: ignore[return-value]


def use_reducer(reducer: Callable[[S, A], S], initial: S) -> tuple[S, Callable[[A], None]]:
    frame, idx = _next_slot()
    if idx >= len(frame.hooks):
        frame.hooks.append(_StateHook(value=initial, pending=[]))

    slot = frame.hooks[idx]
    if not isinstance(slot, _StateHook):
        raise HookError("Hook order/type mismatch for use_reducer.")

    if frame.default_lane is not None and slot.pending:
        visible_pri = _lane_priority(frame.default_lane)
        remaining: list[_PendingUpdate] = []
        for upd in slot.pending:
            if _lane_priority(upd.lane) <= visible_pri:
                slot.value = upd.value
            else:
                remaining.append(upd)
        slot.pending = remaining

    def dispatch(action: A) -> None:
        if frame.schedule_update is None:
            slot.value = reducer(slot.value, action)
            return
        from .concurrent import current_update_lane

        lane = current_update_lane() or frame.default_lane
        next_value = reducer(slot.value, action)
        slot.pending.append(_PendingUpdate(lane=lane, value=next_value))
        frame.schedule_update(lane)

    return slot.value, dispatch  # type: ignore[return-value]


def use_ref(initial: Any = None) -> dict[str, Any]:
    frame, idx = _next_slot()
    if idx >= len(frame.hooks):
        frame.hooks.append({"current": initial})
    return frame.hooks[idx]  # type: ignore[no-any-return]


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
    frame, idx = _next_slot()
    if idx >= len(frame.hooks):
        frame.hooks.append((None, deps))
        old_cleanup, old_deps = None, None
    else:
        old_cleanup, old_deps = frame.hooks[idx]

    def run() -> None:
        cleanup, _ = frame.hooks[idx]
        if cleanup is not None:
            cleanup()
        new_cleanup = effect()
        frame.hooks[idx] = (new_cleanup, deps)

    if deps is None or old_deps is None or deps != old_deps:
        frame.scheduled_passive_effects.append(run)


def use_layout_effect(
    effect: Callable[[], Callable[[], None] | None], deps: tuple[Any, ...] | None = None
) -> None:
    frame, idx = _next_slot()
    if idx >= len(frame.hooks):
        frame.hooks.append((None, deps))
        old_cleanup, old_deps = None, None
    else:
        old_cleanup, old_deps = frame.hooks[idx]

    def run() -> None:
        cleanup, _ = frame.hooks[idx]
        if cleanup is not None:
            cleanup()
        new_cleanup = effect()
        frame.hooks[idx] = (new_cleanup, deps)

    if deps is None or old_deps is None or deps != old_deps:
        frame.scheduled_layout_effects.append(run)


def _is_class_component(component_type: Any) -> bool:
    if not isinstance(component_type, type):
        return False
    try:
        return issubclass(component_type, Component)
    except TypeError:
        return False


# Used by renderers to establish hook context.
def _render_with_hooks(
    fn: Callable[..., Any],
    props: dict[str, Any],
    hooks: list[Any],
    *,
    scheduled_layout_effects: list[Callable[[], None]] | None = None,
    scheduled_passive_effects: list[Callable[[], None]] | None = None,
    schedule_update: Callable[[Any], None] | None = None,
    default_lane: Any | None = None,
) -> Any:
    _push_frame(
        hooks,
        scheduled_layout_effects=scheduled_layout_effects,
        scheduled_passive_effects=scheduled_passive_effects,
        schedule_update=schedule_update,
        default_lane=default_lane,
    )
    try:
        return fn(**props)
    finally:
        _pop_frame()


def _render_component(
    component_type: Any,
    props: dict[str, Any],
    hooks: list[Any],
    *,
    scheduled_layout_effects: list[Callable[[], None]] | None = None,
    scheduled_passive_effects: list[Callable[[], None]] | None = None,
    schedule_update: Callable[[Any], None] | None = None,
    default_lane: Any | None = None,
) -> Any:
    if _is_class_component(component_type):
        instance = component_type(**props)

        def _call_render(**_: Any) -> Any:
            return instance.render()

        return _render_with_hooks(
            _call_render,
            {},
            hooks,
            scheduled_layout_effects=scheduled_layout_effects,
            scheduled_passive_effects=scheduled_passive_effects,
            schedule_update=schedule_update,
            default_lane=default_lane,
        )
    if isinstance(component_type, type):
        raise TypeError(
            "Expected a function component or a subclass of Component, "
            f"got class {component_type!r}"
        )
    if callable(component_type):
        return _render_with_hooks(
            component_type,
            props,
            hooks,
            scheduled_layout_effects=scheduled_layout_effects,
            scheduled_passive_effects=scheduled_passive_effects,
            schedule_update=schedule_update,
            default_lane=default_lane,
        )
    raise TypeError(f"Unsupported component type: {component_type!r}")
