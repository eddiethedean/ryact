from __future__ import annotations

import warnings
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Optional, TypedDict, TypeVar, cast

from .component import Component
from .cache import CacheSignal

S = TypeVar("S")
A = TypeVar("A")
R = TypeVar("R")


class HookError(RuntimeError):
    pass


class RefObject(TypedDict):
    current: Any


@dataclass
class _HookFrame:
    hook_index: int
    hooks: list[Any]
    scheduled_insertion_effects: list[Callable[[], None]]
    scheduled_layout_effects: list[Callable[[], None]]
    scheduled_passive_effects: list[Callable[[], None]]
    scheduled_strict_layout_effects: list[Callable[[], None]]
    scheduled_strict_passive_effects: list[Callable[[], None]]
    schedule_update: Callable[[Any], None] | None
    default_lane: Any | None
    next_id: Callable[[], str] | None
    is_mount: bool
    visible: bool = True
    strict_effects: bool = False
    reappearing: bool = False
    cache_signals: list[CacheSignal] = None  # type: ignore[assignment]
    has_render_phase_update: bool = False


_current_frame: Optional[_HookFrame] = None
_current_commit_phase: str | None = None
_current_commit_stack: str | None = None


def _set_commit_context(*, phase: str | None, stack: str | None) -> None:
    global _current_commit_phase, _current_commit_stack
    _current_commit_phase = phase
    _current_commit_stack = stack


@dataclass
class _PendingUpdate:
    lane: Any
    value: Any
    # If True, ``value`` is a ``setState(prev => next)`` updater; fold in order during apply.
    is_updater: bool = False


@dataclass
class _StateHook:
    value: Any
    pending: list[_PendingUpdate]
    dispatch: Callable[[Any], None] | None = None
    dispatch_ctx: dict[str, Any] | None = None


@dataclass
class _TransitionHook:
    pending: bool


@dataclass
class _IdHook:
    value: str


@dataclass
class _ReducerHook:
    value: Any
    pending: list[_PendingUpdate]
    reducer: Callable[[Any, Any], Any] | None = None
    dispatch: Callable[[Any], None] | None = None
    dispatch_ctx: dict[str, Any] | None = None


def _is_use_state_updater(x: Any) -> bool:
    return callable(x) and not isinstance(x, type)


def _lane_priority(lane: Any) -> int:
    try:
        return int(lane.priority)
    except Exception:
        return 0


def _push_frame(
    hooks: list[Any],
    *,
    scheduled_insertion_effects: list[Callable[[], None]] | None = None,
    scheduled_layout_effects: list[Callable[[], None]] | None = None,
    scheduled_passive_effects: list[Callable[[], None]] | None = None,
    scheduled_strict_layout_effects: list[Callable[[], None]] | None = None,
    scheduled_strict_passive_effects: list[Callable[[], None]] | None = None,
    schedule_update: Callable[[Any], None] | None = None,
    default_lane: Any | None = None,
    next_id: Callable[[], str] | None = None,
    visible: bool = True,
    strict_effects: bool = False,
    reappearing: bool = False,
) -> None:
    global _current_frame
    if _current_frame is not None:
        raise HookError("Nested hook frames are not supported yet.")
    _current_frame = _HookFrame(
        hook_index=0,
        hooks=hooks,
        scheduled_insertion_effects=scheduled_insertion_effects
        if scheduled_insertion_effects is not None
        else [],
        scheduled_layout_effects=scheduled_layout_effects
        if scheduled_layout_effects is not None
        else [],
        scheduled_passive_effects=scheduled_passive_effects
        if scheduled_passive_effects is not None
        else [],
        scheduled_strict_layout_effects=scheduled_strict_layout_effects
        if scheduled_strict_layout_effects is not None
        else [],
        scheduled_strict_passive_effects=scheduled_strict_passive_effects
        if scheduled_strict_passive_effects is not None
        else [],
        schedule_update=schedule_update,
        default_lane=default_lane,
        next_id=next_id,
        is_mount=len(hooks) == 0,
        visible=visible,
        strict_effects=strict_effects,
        reappearing=reappearing,
        cache_signals=[],
        has_render_phase_update=False,
    )


def _pop_frame() -> None:
    global _current_frame
    frame = _current_frame
    if frame is not None:
        for s in getattr(frame, "cache_signals", []) or []:
            try:
                s.aborted = True
            except Exception:
                pass
    _current_frame = None


def _next_slot() -> tuple[_HookFrame, int]:
    if _current_frame is None:
        raise HookError("Hooks can only be used while rendering a component.")
    idx = _current_frame.hook_index
    if not _current_frame.is_mount and idx >= len(_current_frame.hooks):
        raise HookError("Rendered more hooks than during the previous render.")
    _current_frame.hook_index += 1
    return _current_frame, idx


def use_state(initial: S) -> tuple[S, Callable[[S], None]]:
    frame, idx = _next_slot()
    if idx >= len(frame.hooks):
        init_val = initial
        # React supports lazy state initializers: useState(() => value).
        if callable(initial):
            try:
                if frame.strict_effects and frame.is_mount:
                    init_val = initial()  # type: ignore[misc]
                    _ = initial()  # type: ignore[misc]
                else:
                    init_val = initial()  # type: ignore[misc]
            except TypeError:
                # If the callable isn't a 0-arg initializer, treat it as a value.
                init_val = initial
        frame.hooks.append(_StateHook(value=init_val, pending=[]))

    slot = frame.hooks[idx]
    if not isinstance(slot, _StateHook):
        raise HookError("Hook order/type mismatch for use_state.")

    # Apply pending updates visible at this render lane.
    if frame.default_lane is not None and slot.pending:
        visible_pri = _lane_priority(frame.default_lane)
        remaining: list[_PendingUpdate] = []
        for upd in slot.pending:
            if _lane_priority(upd.lane) <= visible_pri:
                if upd.is_updater:
                    try:
                        slot.value = upd.value(slot.value)  # type: ignore[misc, operator]
                    except TypeError:
                        slot.value = upd.value
                else:
                    slot.value = upd.value
            else:
                remaining.append(upd)
        slot.pending = remaining

    if slot.dispatch_ctx is None:
        slot.dispatch_ctx = {}
    slot.dispatch_ctx["schedule_update"] = frame.schedule_update
    slot.dispatch_ctx["default_lane"] = frame.default_lane

    if slot.dispatch is None:
        ctx = slot.dispatch_ctx

        def set_state(next_value: S) -> None:
            schedule_update = ctx.get("schedule_update")
            default_lane = ctx.get("default_lane")
            if schedule_update is None:
                # Non-reconciler renderers (DOM/native) still use an eager model.
                actual = next_value
                if _is_use_state_updater(next_value):
                    try:
                        actual = next_value(slot.value)  # type: ignore[misc]
                    except TypeError:
                        actual = next_value
                slot.value = actual
                return
            is_u = _is_use_state_updater(next_value)
            if not is_u and next_value == slot.value and not slot.pending:
                return
            if _current_commit_phase == "insertion":
                msg = (
                    "Cannot update state from within an insertion effect. "
                    "Move updates to an event handler or a passive effect."
                )
                if _current_commit_stack:
                    msg = msg + "\n\n" + _current_commit_stack
                try:
                    from ryact_testkit.warnings import emit_warning as _emit_warning

                    _emit_warning(msg, stacklevel=3)
                except Exception:
                    pass
                return
            from .concurrent import current_update_lane
            from .reconciler import DEFAULT_LANE

            lane = current_update_lane() or default_lane or DEFAULT_LANE
            if is_u:
                slot.pending.append(
                    _PendingUpdate(lane=lane, value=next_value, is_updater=True)
                )
            else:
                slot.pending.append(
                    _PendingUpdate(lane=lane, value=next_value, is_updater=False)
                )
            # Render-phase restarts: only while actually rendering a function/hook tree
            # (not in passive/layout callbacks, where the hook frame is already popped).
            if _current_frame is not None and _current_commit_phase is None:
                # Do not mutate the captured `frame`: render-phase restarts can happen
                # multiple times and the dispatch closure must flag the *current* attempt.
                _current_frame.has_render_phase_update = True
                return
            schedule_update(lane)

        slot.dispatch = set_state  # type: ignore[assignment]

    return slot.value, cast(Callable[[S], None], slot.dispatch)  # type: ignore[return-value]


def use_reducer(
    reducer: Callable[[S, A], S],
    initial: S,
    init: Callable[[S], S] | None = None,
) -> tuple[S, Callable[[A], None]]:
    frame, idx = _next_slot()
    if idx >= len(frame.hooks):
        value = initial
        if callable(init):
            if frame.strict_effects and frame.is_mount:
                value = init(initial)
                _ = init(initial)
            else:
                value = init(initial)
        frame.hooks.append(_ReducerHook(value=value, pending=[], reducer=reducer))

    slot = frame.hooks[idx]
    if not isinstance(slot, _ReducerHook):
        raise HookError("Hook order/type mismatch for use_reducer.")

    # Always use the reducer from the current render. This prevents stale reducers from
    # being applied to queued actions.
    slot.reducer = reducer

    # Apply pending updates visible at this render lane.
    if frame.default_lane is not None and slot.pending:
        visible_pri = _lane_priority(frame.default_lane)
        remaining: list[_PendingUpdate] = []
        next_value: Any = slot.value
        for upd in slot.pending:
            if _lane_priority(upd.lane) <= visible_pri:
                prev_state = next_value
                next_value = reducer(prev_state, upd.value)  # type: ignore[arg-type]
                if frame.strict_effects:
                    # DEV StrictMode: reducer functions are invoked twice with the same inputs,
                    # but React keeps the first result.
                    _ = reducer(prev_state, upd.value)  # type: ignore[arg-type]
            else:
                remaining.append(upd)
        slot.value = next_value
        slot.pending = remaining

    if slot.dispatch_ctx is None:
        slot.dispatch_ctx = {}
    slot.dispatch_ctx["schedule_update"] = frame.schedule_update
    slot.dispatch_ctx["default_lane"] = frame.default_lane

    if slot.dispatch is None:
        ctx = slot.dispatch_ctx

        def dispatch(action: A) -> None:
            schedule_update = ctx.get("schedule_update")
            default_lane = ctx.get("default_lane")
            if schedule_update is None:
                slot.value = reducer(slot.value, action)
                return
            if _current_commit_phase == "insertion":
                msg = (
                    "Cannot update state from within an insertion effect. "
                    "Move updates to an event handler or a passive effect."
                )
                if _current_commit_stack:
                    msg = msg + "\n\n" + _current_commit_stack
                try:
                    from ryact_testkit.warnings import emit_warning as _emit_warning

                    _emit_warning(msg, stacklevel=3)
                except Exception:
                    pass
                return
            from .concurrent import current_update_lane
            from .reconciler import DEFAULT_LANE

            lane = current_update_lane() or default_lane or DEFAULT_LANE
            # Do not eagerly bail out: queued actions may become relevant if other updates
            # in the same batch (props/state) change the reducer's behavior.
            slot.pending.append(_PendingUpdate(lane=lane, value=action))
            if _current_frame is not None and _current_commit_phase is None:
                # Do not mutate the captured `frame`: flag the current render attempt.
                _current_frame.has_render_phase_update = True
                return
            schedule_update(lane)

        slot.dispatch = dispatch  # type: ignore[assignment]

    return slot.value, cast(Callable[[A], None], slot.dispatch)  # type: ignore[return-value]


def use_ref(initial: Any = None) -> RefObject:
    frame, idx = _next_slot()
    if idx >= len(frame.hooks):
        frame.hooks.append({"current": initial})
    if not isinstance(frame.hooks[idx], dict):
        raise HookError("Hook order/type mismatch for use_ref.")
    return cast(RefObject, frame.hooks[idx])


def _warn_if_invalid_deps(deps: Any, *, hook_name: str) -> None:
    from .dev import is_dev

    if deps is None or isinstance(deps, tuple) or not is_dev():
        return
    msg = f"{hook_name} received a final argument that is not an array (tuple in Python)."
    try:
        from ryact_testkit.warnings import emit_warning as _emit_warning

        _emit_warning(msg, stacklevel=4)
    except Exception:
        warnings.warn(msg, RuntimeWarning, stacklevel=4)


def _warn_if_switching_deps(*, hook_name: str, old_deps: Any, deps: Any) -> None:
    from .dev import is_dev

    if not is_dev():
        return
    if old_deps is None or deps is not None:
        return
    msg = f"{hook_name} dependencies argument changed from defined to undefined."
    try:
        from ryact_testkit.warnings import emit_warning as _emit_warning

        _emit_warning(msg, stacklevel=4)
    except Exception:
        warnings.warn(msg, RuntimeWarning, stacklevel=4)


def _tag_effect(fn: Callable[[], None], *, phase: str) -> Callable[[], None]:
    try:
        fn._ryact_effect_phase = phase  # type: ignore[attr-defined]
    except Exception:
        pass
    return fn


def use_memo(factory: Callable[[], R], deps: tuple[Any, ...] | None = None) -> R:
    frame, idx = _next_slot()
    _warn_if_invalid_deps(deps, hook_name="use_memo")
    if idx >= len(frame.hooks):
        if frame.strict_effects and frame.is_mount:
            value = factory()
            _ = factory()
        else:
            value = factory()
        frame.hooks.append((value, deps))
        return value
    slot = frame.hooks[idx]
    if not isinstance(slot, tuple) or len(slot) != 2:
        raise HookError("Hook order/type mismatch for use_memo.")
    value, old_deps = slot
    _warn_if_switching_deps(hook_name="use_memo", old_deps=old_deps, deps=deps)
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
    _warn_if_invalid_deps(deps, hook_name="use_effect")
    if not frame.visible:
        # Offscreen/hidden trees: effects are disconnected.
        if idx >= len(frame.hooks):
            frame.hooks.append((None, None, "passive"))
        else:
            frame.hooks[idx] = (None, None, "passive")
        return
    if idx >= len(frame.hooks):
        frame.hooks.append((None, deps, "passive"))
        old_cleanup, old_deps = None, None
    else:
        slot = frame.hooks[idx]
        if not isinstance(slot, tuple) or len(slot) not in (2, 3):
            raise HookError("Hook order/type mismatch for use_effect.")
        old_cleanup, old_deps = slot[0], slot[1]
    _warn_if_switching_deps(hook_name="use_effect", old_deps=old_deps, deps=deps)

    if deps is None or old_deps is None or deps != old_deps:
        def destroy() -> None:
            slot2 = frame.hooks[idx]
            cleanup = slot2[0] if isinstance(slot2, tuple) and len(slot2) >= 1 else None
            if cleanup is not None and callable(cleanup):
                cleanup()

        def create() -> None:
            new_cleanup = effect()
            frame.hooks[idx] = (
                new_cleanup if (new_cleanup is None or callable(new_cleanup)) else None,
                deps,
                "passive",
            )

        frame.scheduled_passive_effects.append(_tag_effect(destroy, phase="destroy"))
        frame.scheduled_passive_effects.append(_tag_effect(create, phase="create"))
        if frame.strict_effects and (frame.is_mount or frame.reappearing):
            frame.scheduled_strict_passive_effects.append(_tag_effect(destroy, phase="destroy"))
            frame.scheduled_strict_passive_effects.append(_tag_effect(create, phase="create"))


def use_layout_effect(
    effect: Callable[[], Callable[[], None] | None], deps: tuple[Any, ...] | None = None
) -> None:
    frame, idx = _next_slot()
    _warn_if_invalid_deps(deps, hook_name="use_layout_effect")
    if not frame.visible:
        if idx >= len(frame.hooks):
            frame.hooks.append((None, None, "layout"))
        else:
            frame.hooks[idx] = (None, None, "layout")
        return
    if idx >= len(frame.hooks):
        frame.hooks.append((None, deps, "layout"))
        old_cleanup, old_deps = None, None
    else:
        slot = frame.hooks[idx]
        if not isinstance(slot, tuple) or len(slot) not in (2, 3):
            raise HookError("Hook order/type mismatch for use_layout_effect.")
        old_cleanup, old_deps = slot[0], slot[1]
    _warn_if_switching_deps(hook_name="use_layout_effect", old_deps=old_deps, deps=deps)

    if deps is None or old_deps is None or deps != old_deps:
        def destroy() -> None:
            slot2 = frame.hooks[idx]
            cleanup = slot2[0] if isinstance(slot2, tuple) and len(slot2) >= 1 else None
            if cleanup is not None and callable(cleanup):
                cleanup()

        def create() -> None:
            new_cleanup = effect()
            frame.hooks[idx] = (
                new_cleanup if (new_cleanup is None or callable(new_cleanup)) else None,
                deps,
                "layout",
            )

        frame.scheduled_layout_effects.append(_tag_effect(destroy, phase="destroy"))
        frame.scheduled_layout_effects.append(_tag_effect(create, phase="create"))
        if frame.strict_effects and (frame.is_mount or frame.reappearing):
            frame.scheduled_strict_layout_effects.append(_tag_effect(destroy, phase="destroy"))
            frame.scheduled_strict_layout_effects.append(_tag_effect(create, phase="create"))


def use_insertion_effect(
    effect: Callable[[], Callable[[], None] | None], deps: tuple[Any, ...] | None = None
) -> None:
    frame, idx = _next_slot()
    _warn_if_invalid_deps(deps, hook_name="use_insertion_effect")
    if not frame.visible:
        if idx >= len(frame.hooks):
            frame.hooks.append((None, None, "insertion"))
        else:
            frame.hooks[idx] = (None, None, "insertion")
        return
    if idx >= len(frame.hooks):
        frame.hooks.append((None, deps, "insertion"))
        old_cleanup, old_deps = None, None
    else:
        slot = frame.hooks[idx]
        if not isinstance(slot, tuple) or len(slot) not in (2, 3):
            raise HookError("Hook order/type mismatch for use_insertion_effect.")
        old_cleanup, old_deps = slot[0], slot[1]
    _warn_if_switching_deps(hook_name="use_insertion_effect", old_deps=old_deps, deps=deps)

    if deps is None or old_deps is None or deps != old_deps:
        def destroy() -> None:
            slot2 = frame.hooks[idx]
            cleanup = slot2[0] if isinstance(slot2, tuple) and len(slot2) >= 1 else None
            if cleanup is not None and callable(cleanup):
                cleanup()

        def create() -> None:
            new_cleanup = effect()
            frame.hooks[idx] = (
                new_cleanup if (new_cleanup is None or callable(new_cleanup)) else None,
                deps,
                "insertion",
            )

        frame.scheduled_insertion_effects.append(_tag_effect(destroy, phase="destroy"))
        frame.scheduled_insertion_effects.append(_tag_effect(create, phase="create"))


def use_deferred_value(value: Any, initial_value: Any | None = None) -> Any:
    from .reconciler import TRANSITION_LANE

    # Minimal slice (Milestone 22):
    # - If `initial_value` is provided, return it on mount (unless rendering in a transition lane).
    # - After commit, "catch up" to the latest value on the next flush.
    # - If we're rendering a transition update, don't defer.
    frame0 = _current_frame
    if frame0 is None:
        return value
    in_transition = frame0.default_lane is TRANSITION_LANE

    deferred, set_deferred = use_state(
        initial_value
        if (frame0.is_mount and initial_value is not None and not in_transition)
        else value
    )

    def sync_after_commit() -> None:
        # Catch up after commit (layout is deterministic in noop host).
        if deferred != value:
            set_deferred(value)

    if not in_transition:
        # Note: scheduled effects will run post-commit in deterministic order.
        def _eff() -> None:
            sync_after_commit()
            return None

        use_layout_effect(_eff, (value,))

    return value if in_transition else deferred


def use_sync_external_store(
    subscribe: Callable[[Callable[[], None]], Callable[[], None]],
    get_snapshot: Callable[[], Any],
) -> Any:
    snapshot, set_snapshot = use_state(get_snapshot())

    def on_store_change() -> None:
        set_snapshot(get_snapshot())

    def eff() -> Callable[[], None] | None:
        return subscribe(on_store_change)

    use_effect(eff, ())

    # Minimal slice (Milestone 22): detect/pick up mutations that occur between render and layout.
    def recheck_before_layout() -> None:
        next_snap = get_snapshot()
        if next_snap != snapshot:
            set_snapshot(next_snap)

    def _eff2() -> None:
        recheck_before_layout()
        return None

    use_layout_effect(_eff2, (snapshot,))
    return snapshot


def use_transition() -> tuple[bool, Callable[[Callable[[], None]], None]]:
    frame, idx = _next_slot()
    if idx >= len(frame.hooks):
        frame.hooks.append(_TransitionHook(pending=False))
    slot = frame.hooks[idx]
    if not isinstance(slot, _TransitionHook):
        raise HookError("Hook order/type mismatch for use_transition.")

    def start(fn: Callable[[], None]) -> None:
        from .concurrent import start_transition as _start_transition
        from .reconciler import TRANSITION_LANE

        slot.pending = True
        if frame.schedule_update is not None:
            frame.schedule_update(TRANSITION_LANE)
        _start_transition(fn)

    return slot.pending, start


_global_id_counter = 0


def use_id() -> str:
    """
    Minimal `useId` surface.

    Deterministic id allocation is renderer-driven when available (e.g. noop reconciler).
    """
    global _global_id_counter
    frame, idx = _next_slot()
    if idx >= len(frame.hooks):
        if frame.next_id is not None:
            value = frame.next_id()
        else:
            _global_id_counter += 1
            value = f"rid-{_global_id_counter}"
        frame.hooks.append(_IdHook(value=value))
    slot = frame.hooks[idx]
    if not isinstance(slot, _IdHook):
        raise HookError("Hook order/type mismatch for use_id.")
    return slot.value


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
    scheduled_insertion_effects: list[Callable[[], None]] | None = None,
    scheduled_layout_effects: list[Callable[[], None]] | None = None,
    scheduled_passive_effects: list[Callable[[], None]] | None = None,
    scheduled_strict_layout_effects: list[Callable[[], None]] | None = None,
    scheduled_strict_passive_effects: list[Callable[[], None]] | None = None,
    schedule_update: Callable[[Any], None] | None = None,
    default_lane: Any | None = None,
    next_id: Callable[[], str] | None = None,
    visible: bool = True,
    strict_effects: bool = False,
    reappearing: bool = False,
) -> Any:
    max_restarts = 25
    attempt = 0
    while True:
        attempt += 1
        if attempt > max_restarts:
            raise HookError("Too many re-renders. The number of renders has exceeded the limit.")

        # For render-phase restarts, we must discard effects scheduled in aborted attempts.
        ins_len = len(scheduled_insertion_effects or [])
        lay_len = len(scheduled_layout_effects or [])
        pas_len = len(scheduled_passive_effects or [])
        sl_len = len(scheduled_strict_layout_effects or [])
        sp_len = len(scheduled_strict_passive_effects or [])

        _push_frame(
            hooks,
            scheduled_insertion_effects=scheduled_insertion_effects,
            scheduled_layout_effects=scheduled_layout_effects,
            scheduled_passive_effects=scheduled_passive_effects,
            scheduled_strict_layout_effects=scheduled_strict_layout_effects,
            scheduled_strict_passive_effects=scheduled_strict_passive_effects,
            schedule_update=schedule_update,
            default_lane=default_lane,
            next_id=next_id,
            visible=visible,
            strict_effects=strict_effects,
            reappearing=reappearing,
        )
        ok = False
        try:
            result = fn(**props)
            ok = True
        finally:
            frame = _current_frame
            try:
                if (
                    ok
                    and frame is not None
                    and not frame.is_mount
                    and frame.hook_index != len(frame.hooks)
                ):
                    raise HookError("Rendered fewer hooks than during the previous render.")
            finally:
                _pop_frame()

        if frame is not None and frame.has_render_phase_update:
            if scheduled_insertion_effects is not None:
                del scheduled_insertion_effects[ins_len:]
            if scheduled_layout_effects is not None:
                del scheduled_layout_effects[lay_len:]
            if scheduled_passive_effects is not None:
                del scheduled_passive_effects[pas_len:]
            if scheduled_strict_layout_effects is not None:
                del scheduled_strict_layout_effects[sl_len:]
            if scheduled_strict_passive_effects is not None:
                del scheduled_strict_passive_effects[sp_len:]
            continue

        return result


def _render_component(
    component_type: Any,
    props: dict[str, Any],
    hooks: list[Any],
    *,
    scheduled_insertion_effects: list[Callable[[], None]] | None = None,
    scheduled_layout_effects: list[Callable[[], None]] | None = None,
    scheduled_passive_effects: list[Callable[[], None]] | None = None,
    schedule_update: Callable[[Any], None] | None = None,
    default_lane: Any | None = None,
    next_id: Callable[[], str] | None = None,
) -> Any:
    if _is_class_component(component_type):
        instance = component_type(**props)

        def _call_render(**_: Any) -> Any:
            return instance.render()

        return _render_with_hooks(
            _call_render,
            {},
            hooks,
            scheduled_insertion_effects=scheduled_insertion_effects,
            scheduled_layout_effects=scheduled_layout_effects,
            scheduled_passive_effects=scheduled_passive_effects,
            schedule_update=schedule_update,
            default_lane=default_lane,
            next_id=next_id,
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
            scheduled_insertion_effects=scheduled_insertion_effects,
            scheduled_layout_effects=scheduled_layout_effects,
            scheduled_passive_effects=scheduled_passive_effects,
            schedule_update=schedule_update,
            default_lane=default_lane,
            next_id=next_id,
        )
    raise TypeError(f"Unsupported component type: {component_type!r}")
