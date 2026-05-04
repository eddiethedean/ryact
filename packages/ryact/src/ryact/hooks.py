from __future__ import annotations

import inspect
import warnings
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass
from typing import Any, Optional, TypedDict, TypeVar, cast

from .cache import CacheSignal
from .component import Component
from .context import Context, ContextConsumerMarker, context_provider, create_context
from .ref import Ref

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
    # Second DEV StrictMode function render: hooks exist but effect mount work still applies.
    strict_remaining_mount_pass: bool = False
    cache_signals: list[CacheSignal] | None = None
    has_render_phase_update: bool = False
    # True when ``hooks._render_component`` is driving a class ``render()`` (not a function body).
    from_class_render: bool = False
    # True once a render throws Suspense/Suspend. While suspended, hooks must be disabled
    # so userland `try/except` cannot catch and keep calling hooks.
    suspended: bool = False
    # DEV-ish: async client components are not allowed to call hooks.
    async_component: bool = False
    async_hook_warned: bool = False
    # React legacy contextTypes snapshot for function components / forwardRef render fns.
    legacy_context: dict[str, Any] | None = None
    _cache_for_type: dict[Any, Any] | None = None


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
    # True when enqueued during the render phase of this component.
    render_phase: bool = False


@dataclass
class _StateHook:
    value: Any
    pending: list[_PendingUpdate]
    dispatch: Callable[[Any], None] | None = None
    dispatch_ctx: dict[str, Any] | None = None
    _render_phase_base: Any | None = None


@dataclass
class _TransitionHook:
    pending: bool
    error: BaseException | None = None


@dataclass
class _IdHook:
    value: str


@dataclass
class _OptimisticHook:
    passthrough: Any
    reducer: Callable[[Any, Any], Any] | None
    # Each pending optimistic update is scoped to a specific async action thenable.
    pending: list[tuple[Any, Any]]  # (action, value)
    dispatch: Callable[[Any], None] | None = None


@dataclass
class _ReducerHook:
    value: Any
    pending: list[_PendingUpdate]
    reducer: Callable[[Any, Any], Any] | None = None
    dispatch: Callable[[Any], None] | None = None
    dispatch_ctx: dict[str, Any] | None = None
    _render_phase_base: Any | None = None


@dataclass
class _DebugValueHook:
    label: str


@dataclass
class FormStatusSnapshot:
    """Minimal snapshot for ``use_form_status`` (React 19 analogue)."""

    pending: bool = False
    data: Any = None
    method: str = "get"
    action: Any = None


_form_status_context: Context[FormStatusSnapshot] | None = None


def _form_status_ctx() -> Context[FormStatusSnapshot]:
    global _form_status_context
    if _form_status_context is None:
        _form_status_context = create_context(FormStatusSnapshot())
    return _form_status_context


def form_status_provider(status: FormStatusSnapshot, child: Any) -> Any:
    return context_provider(_form_status_ctx(), status, child)


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
    strict_remaining_mount_pass: bool = False,
    from_class_render: bool = False,
    legacy_context: dict[str, Any] | None = None,
) -> None:
    global _current_frame
    if _current_frame is not None:
        raise HookError("Nested hook frames are not supported yet.")
    _current_frame = _HookFrame(
        hook_index=0,
        hooks=hooks,
        scheduled_insertion_effects=scheduled_insertion_effects if scheduled_insertion_effects is not None else [],
        scheduled_layout_effects=scheduled_layout_effects if scheduled_layout_effects is not None else [],
        scheduled_passive_effects=scheduled_passive_effects if scheduled_passive_effects is not None else [],
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
        strict_remaining_mount_pass=strict_remaining_mount_pass,
        cache_signals=[],
        has_render_phase_update=False,
        from_class_render=from_class_render,
        legacy_context=legacy_context,
    )


def _pop_frame() -> None:
    global _current_frame
    frame = _current_frame
    if frame is not None:
        for s in getattr(frame, "cache_signals", []) or []:
            with suppress(Exception):
                s.aborted = True
    _current_frame = None


def _next_slot() -> tuple[_HookFrame, int]:
    if _current_frame is None:
        raise HookError("Hooks can only be used while rendering a component.")
    if getattr(_current_frame, "suspended", False):
        raise HookError("Hooks cannot be called while a component is suspended.")
    if getattr(_current_frame, "async_component", False) and not getattr(_current_frame, "async_hook_warned", False):
        try:
            from ryact_testkit.warnings import emit_warning as _emit_warning

            _emit_warning(
                "warn if async client component calls a hook",
                stacklevel=3,
            )
            _current_frame.async_hook_warned = True
        except Exception:
            pass
    idx = _current_frame.hook_index
    if not _current_frame.is_mount and idx >= len(_current_frame.hooks):
        raise HookError("Rendered more hooks than during the previous render.")
    _current_frame.hook_index += 1
    return _current_frame, idx


def _mark_current_frame_suspended() -> None:
    frame = _current_frame
    if frame is not None:
        frame.suspended = True


def use_state(initial: S) -> tuple[S, Callable[[Any], None]]:
    frame, idx = _next_slot()
    if idx >= len(frame.hooks):
        init_val = initial
        # React supports lazy state initializers: useState(() => value).
        if callable(initial):
            init_fn = cast(Callable[[], Any], initial)
            try:
                if frame.strict_effects and frame.is_mount:
                    init_val = init_fn()
                    _ = init_fn()
                else:
                    init_val = init_fn()
            except TypeError:
                # If the callable isn't a 0-arg initializer, treat it as a value.
                init_val = initial
        frame.hooks.append(_StateHook(value=init_val, pending=[]))

    slot = frame.hooks[idx]
    if not isinstance(slot, _StateHook):
        raise HookError("Hook order/type mismatch for use_state.")

    # Apply pending updates visible at this render lane.
    if frame.default_lane is not None and slot.pending:
        base_before = slot.value
        applied_render_phase = False
        visible_pri = _lane_priority(frame.default_lane)
        remaining: list[_PendingUpdate] = []
        for upd in slot.pending:
            if _lane_priority(upd.lane) <= visible_pri:
                if upd.is_updater:
                    try:
                        slot.value = cast(Callable[[Any], Any], upd.value)(slot.value)
                    except TypeError:
                        slot.value = upd.value
                else:
                    slot.value = upd.value
                if bool(getattr(upd, "render_phase", False)):
                    applied_render_phase = True
            else:
                remaining.append(upd)
        slot.pending = remaining
        if applied_render_phase:
            slot._render_phase_base = base_before

    if slot.dispatch_ctx is None:
        slot.dispatch_ctx = {}
    slot.dispatch_ctx["schedule_update"] = frame.schedule_update
    slot.dispatch_ctx["default_lane"] = frame.default_lane
    slot.dispatch_ctx["_owner_frame_id"] = id(frame)

    if slot.dispatch is None:
        ctx = slot.dispatch_ctx

        def set_state(next_value: Any) -> None:
            schedule_update = ctx.get("schedule_update")
            default_lane = ctx.get("default_lane")
            if schedule_update is None:
                # Non-reconciler renderers (DOM/native) still use an eager model.
                actual = next_value
                if _is_use_state_updater(next_value):
                    try:
                        actual = cast(Callable[[Any], Any], next_value)(slot.value)
                    except TypeError:
                        actual = next_value
                slot.value = actual
                return
            is_u = _is_use_state_updater(next_value)
            if not is_u and next_value == slot.value and not slot.pending:
                return
            # Internal optimization: render-phase updates that compute the same state
            # should not trigger a render restart.
            if is_u and _current_frame is not None and _current_commit_phase is None and not slot.pending:
                try:
                    actual = cast(Callable[[Any], Any], next_value)(slot.value)
                except TypeError:
                    actual = next_value
                if actual == slot.value:
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
            is_render_phase = _current_frame is not None and _current_commit_phase is None
            if is_u:
                slot.pending.append(
                    _PendingUpdate(lane=lane, value=next_value, is_updater=True, render_phase=is_render_phase)
                )
            else:
                slot.pending.append(
                    _PendingUpdate(lane=lane, value=next_value, is_updater=False, render_phase=is_render_phase)
                )
            # Render-phase restarts: only while actually rendering a function/hook tree
            # (not in passive/layout callbacks, where the hook frame is already popped).
            if is_render_phase:
                # Restarting render is only valid for the component currently being rendered.
                # Updates targeting a different component should warn and be scheduled normally.
                cf = _current_frame
                if cf is not None and ctx.get("_owner_frame_id") == id(cf):
                    # Do not mutate the captured `frame`: render-phase restarts can happen
                    # multiple times and the dispatch closure must flag the *current* attempt.
                    cf.has_render_phase_update = True
                    return
                try:
                    from ryact_testkit.warnings import emit_warning as _emit_warning

                    _emit_warning(
                        "Cannot update a component while rendering a different component.",
                        stacklevel=3,
                    )
                except Exception:
                    pass
            schedule_update(lane)

        slot.dispatch = set_state  # type: ignore[assignment]

    return slot.value, cast(Callable[[Any], None], slot.dispatch)  # type: ignore[return-value]


def use_reducer(
    reducer: Callable[[S, A], S],
    initial: S,
    init: Callable[[S], S] | None = None,
) -> tuple[S, Callable[[Any], None]]:
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
        base_before = slot.value
        applied_render_phase = False
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
                if bool(getattr(upd, "render_phase", False)):
                    applied_render_phase = True
            else:
                remaining.append(upd)
        slot.value = next_value
        slot.pending = remaining
        if applied_render_phase:
            slot._render_phase_base = base_before

    if slot.dispatch_ctx is None:
        slot.dispatch_ctx = {}
    slot.dispatch_ctx["schedule_update"] = frame.schedule_update
    slot.dispatch_ctx["default_lane"] = frame.default_lane
    slot.dispatch_ctx["_owner_frame_id"] = id(frame)

    if slot.dispatch is None:
        ctx = slot.dispatch_ctx

        def dispatch(action: Any) -> None:
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
            is_render_phase = _current_frame is not None and _current_commit_phase is None
            # Do not eagerly bail out: queued actions may become relevant if other updates
            # in the same batch (props/state) change the reducer's behavior.
            slot.pending.append(_PendingUpdate(lane=lane, value=action, render_phase=is_render_phase))
            if is_render_phase:
                cf2 = _current_frame
                if cf2 is not None and ctx.get("_owner_frame_id") == id(cf2):
                    # Do not mutate the captured `frame`: flag the current render attempt.
                    cf2.has_render_phase_update = True
                    return
                try:
                    from ryact_testkit.warnings import emit_warning as _emit_warning

                    _emit_warning(
                        "Cannot update a component while rendering a different component.",
                        stacklevel=3,
                    )
                except Exception:
                    pass
            schedule_update(lane)

        slot.dispatch = dispatch  # type: ignore[assignment]

    return slot.value, cast(Callable[[Any], None], slot.dispatch)  # type: ignore[return-value]


def use_ref(initial: Any = None) -> RefObject:
    frame, idx = _next_slot()
    if idx >= len(frame.hooks):
        frame.hooks.append({"current": initial})
    if not isinstance(frame.hooks[idx], dict):
        raise HookError("Hook order/type mismatch for use_ref.")
    return cast(RefObject, frame.hooks[idx])


def use_context(context: Any) -> Any:
    """Read the nearest provider value for ``context`` (React ``useContext``)."""

    if isinstance(context, ContextConsumerMarker):
        from .dev import is_dev

        if is_dev():
            warnings.warn(
                "Calling useContext(Context.Consumer) is not supported and will cause bugs. "
                "Did you mean to call useContext(Context) instead?",
                RuntimeWarning,
                stacklevel=2,
            )
        context = context.context
    if not isinstance(context, Context):
        raise TypeError(f"use_context expected a Context, got {type(context)!r}")

    if _current_frame is None or _current_frame.from_class_render:
        raise HookError("Invalid hook call. Hooks can only be called inside of the body of a function component.")

    frame, idx = _next_slot()
    value = context._get()
    if idx >= len(frame.hooks):
        frame.hooks.append(context)
    else:
        prev = frame.hooks[idx]
        if prev is not context:
            raise HookError("use_context must receive the same Context object on every render.")
    return value


def get_legacy_context() -> dict[str, Any]:
    """
    Snapshot of legacy ``contextTypes`` values for the current function component render.

    Class components should read ``Component.context`` (``contextType`` or legacy map).
    """

    if _current_frame is None or _current_frame.from_class_render:
        raise HookError("get_legacy_context() can only be called from a function component body.")
    snap = _current_frame.legacy_context
    if snap is None:
        return {}
    return dict(snap)


def use_debug_value(value: Any, formatter: Callable[[Any], Any] | None = None) -> None:
    """DEV-only debug label hook (React ``useDebugValue`` subset)."""

    from .dev import is_dev

    frame, idx = _next_slot()
    label = ""
    if is_dev():
        try:
            label = formatter(value) if formatter is not None else repr(value)
        except Exception:
            label = "<use_debug_value format error>"
    if idx >= len(frame.hooks):
        frame.hooks.append(_DebugValueHook(label=label))
    else:
        slot = frame.hooks[idx]
        if not isinstance(slot, _DebugValueHook):
            raise HookError("Hook order/type mismatch for use_debug_value.")
        slot.label = label


def use_form_status() -> FormStatusSnapshot:
    """Read nearest form status context (host wiring may extend later)."""

    return use_context(_form_status_ctx())


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
    with suppress(Exception):
        cast(Any, fn)._ryact_effect_phase = phase
    return fn


def use_memo(factory: Callable[[], Any], deps: Any = None) -> Any:
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


def use_callback(fn: Callable[..., Any], deps: Any = None) -> Callable[..., Any]:
    return use_memo(lambda: fn, deps)


def use_effect(effect: Callable[[], Any], deps: Any = None) -> None:
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

    needs_fire = (
        deps is None
        or old_deps is None
        or deps != old_deps
        or (frame.strict_remaining_mount_pass and old_cleanup is None and old_deps == deps)
    )
    if needs_fire:

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
        if frame.strict_effects and (frame.is_mount or frame.reappearing or frame.strict_remaining_mount_pass):
            frame.scheduled_strict_passive_effects.append(_tag_effect(destroy, phase="destroy"))
            frame.scheduled_strict_passive_effects.append(_tag_effect(create, phase="create"))


def use_layout_effect(effect: Callable[[], Any], deps: Any = None) -> None:
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

    needs_fire = (
        deps is None
        or old_deps is None
        or deps != old_deps
        or (frame.strict_remaining_mount_pass and old_cleanup is None and old_deps == deps)
    )
    if needs_fire:

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
        if frame.strict_effects and (frame.is_mount or frame.reappearing or frame.strict_remaining_mount_pass):
            frame.scheduled_strict_layout_effects.append(_tag_effect(destroy, phase="destroy"))
            frame.scheduled_strict_layout_effects.append(_tag_effect(create, phase="create"))


def use_insertion_effect(effect: Callable[[], Any], deps: Any = None) -> None:
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

    needs_fire = (
        deps is None
        or old_deps is None
        or deps != old_deps
        or (frame.strict_remaining_mount_pass and old_cleanup is None and old_deps == deps)
    )
    if needs_fire:

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


def use_imperative_handle(
    ref: Any,
    factory: Callable[[], Any],
    deps: Any = None,
) -> None:
    """Attach a mutable imperative instance to ``ref`` (React ``useImperativeHandle`` subset)."""

    def effect() -> Callable[[], None] | None:
        handle = factory()
        if isinstance(ref, Ref):
            ref.current = handle
        elif isinstance(ref, dict) and "current" in ref:
            ref["current"] = handle
        elif callable(ref):
            ref(handle)
        else:
            raise TypeError("use_imperative_handle expects a Ref, ref dict, or callback ref.")

        def cleanup() -> None:
            if isinstance(ref, Ref):
                ref.current = None
            elif isinstance(ref, dict) and "current" in ref:
                ref["current"] = None
            elif callable(ref):
                ref(None)

        return cleanup

    use_layout_effect(effect, deps)


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
        initial_value if (frame0.is_mount and initial_value is not None and not in_transition) else value
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
        frame.hooks.append(_TransitionHook(pending=False, error=None))
    slot = frame.hooks[idx]
    if not isinstance(slot, _TransitionHook):
        raise HookError("Hook order/type mismatch for use_transition.")

    # Surface async action errors during render.
    if slot.error is not None:
        err = slot.error
        slot.error = None
        # Root-level retry would swallow a transient render error by retrying and succeeding
        # on the second attempt (since we've cleared the slot). Async action errors should
        # surface as uncaught render errors.
        with suppress(Exception):
            err._ryact_no_root_retry = True
        raise err

    def start(fn: Callable[[], Any]) -> Any:
        from .concurrent import Thenable
        from .concurrent import start_transition as _start_transition
        from .reconciler import TRANSITION_LANE

        # Render-phase startTransition: upstream warns and does not treat this like a real
        # transition. If we schedule a transition-lane update here, the pending update is not
        # visible to the current DEFAULT render, which can cause infinite render-phase restarts.
        if _current_frame is not None and _current_commit_phase is None and frame is _current_frame:
            try:
                from ryact_testkit.warnings import emit_warning as _emit_warning

                _emit_warning(
                    "calling startTransition inside render phase",
                    stacklevel=3,
                )
            except Exception:
                pass
            # Run the callback without setting a transition lane so any render-phase state updates
            # are visible to the current render lane and can converge.
            return fn()

        slot.pending = True
        if frame.schedule_update is not None:
            frame.schedule_update(TRANSITION_LANE)
        result = _start_transition(fn)
        if isinstance(result, Thenable):
            # Async action: pending remains true until the thenable settles.
            def done() -> None:
                # Clear pending and schedule a retry to either commit the final state
                # or surface the error on the next render.
                if result.status == "rejected":
                    slot.error = result.error
                slot.pending = False
                if frame.schedule_update is not None:
                    frame.schedule_update(TRANSITION_LANE)

            result.then(done)
            return result
        # Sync action: keep pending True through the transition commit. The noop host
        # clears it after committing the transition-lane update and schedules a follow-up
        # render so callers observe pending=True then pending=False across commits.
        return result

    return slot.pending, start


def use_action_state(
    action: Callable[[Any, Any], Any],
    initial_state: Any,
    permalink: str | None = None,
) -> tuple[Any, Callable[..., None], bool]:
    """Form/action state hook (React ``useActionState`` subset; ``permalink`` reserved)."""

    _ = permalink
    state, set_state = use_state(initial_state)
    is_pending, start_transition_fn = use_transition()

    def dispatch(payload: Any = None, *_args: Any, **_kwargs: Any) -> None:
        def run() -> None:
            set_state(lambda prev: action(prev, payload))

        start_transition_fn(run)

    return state, dispatch, is_pending


def use_optimistic(
    passthrough: Any, reducer: Callable[[Any, Any], Any] | None = None
) -> tuple[Any, Callable[[Any], None]]:
    """
    Minimal `useOptimistic` surface (AsyncActions burndown).

    - Returns the passthrough value when no async actions are pending.
    - While an async action is pending, optimistic updates are applied on top of the passthrough.
    - Optimistic updates are scoped to the latest started async action thenable.
    """
    frame, idx = _next_slot()
    if idx >= len(frame.hooks):
        frame.hooks.append(_OptimisticHook(passthrough=passthrough, reducer=reducer, pending=[]))
    slot = frame.hooks[idx]
    if not isinstance(slot, _OptimisticHook):
        raise HookError("Hook order/type mismatch for use_optimistic.")

    # Subscribe once to async-action settlement so we can rerender and clear/rebase.
    if not bool(getattr(slot, "_listener_registered", False)):
        from .concurrent import on_async_action_settled

        def _notify() -> None:
            if frame.schedule_update is not None:
                frame.schedule_update(frame.default_lane)

        on_async_action_settled(_notify)
        with suppress(Exception):
            slot._listener_registered = True

    # Update passthrough/reducer.
    slot.passthrough = passthrough
    if reducer is not None:
        slot.reducer = reducer

    def dispatch(value: Any) -> None:
        from .concurrent import current_async_action, has_pending_async_actions
        from .dev import is_dev

        # DEV warning: upstream expects useOptimistic to be used inside transitions.
        if is_dev() and not has_pending_async_actions():
            warnings.warn(
                "useOptimistic warns if outside of a transition",
                RuntimeWarning,
                stacklevel=2,
            )
            return
        action = current_async_action()
        if action is None:
            return
        slot.pending.append((action, value))
        if frame.schedule_update is not None:
            frame.schedule_update(frame.default_lane)

    slot.dispatch = dispatch

    # Compute value.
    from .concurrent import has_pending_async_actions, is_async_action_pending

    if not has_pending_async_actions():
        # Clear pending optimistic updates once all actions complete.
        slot.pending.clear()
        return passthrough, dispatch

    # Drop updates for actions that already settled.
    slot.pending[:] = [(a, v) for (a, v) in slot.pending if is_async_action_pending(a)]

    # Rebase on passthrough.
    out = passthrough
    for _action, v in list(slot.pending):
        out = slot.reducer(out, v) if slot.reducer is not None else v
    return out, dispatch


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
    strict_remaining_mount_pass: bool = False,
    from_class_render: bool = False,
    legacy_context: dict[str, Any] | None = None,
) -> Any:
    max_restarts = 25
    attempt = 0
    from .concurrent import Suspend

    def _snapshot_pending_lengths(hs: list[Any]) -> tuple[int, dict[int, int]]:
        out: dict[int, int] = {}
        for i, slot in enumerate(hs):
            pending = getattr(slot, "pending", None)
            if isinstance(pending, list):
                out[i] = len(pending)
        return len(hs), out

    def _rollback_pending_lengths(hs: list[Any], initial_len: int, marks: dict[int, int]) -> None:
        # New hook slots created during the suspended attempt should not retain queued updates.
        for i in range(initial_len, len(hs)):
            pending = getattr(hs[i], "pending", None)
            if isinstance(pending, list) and pending:
                pending.clear()
        for i, before in marks.items():
            if i >= len(hs):
                continue
            slot = hs[i]
            pending = getattr(slot, "pending", None)
            if isinstance(pending, list) and len(pending) > before:
                del pending[before:]

    def _snapshot_hook_values(hs: list[Any]) -> dict[int, Any]:
        out: dict[int, Any] = {}
        for i, slot in enumerate(hs):
            if hasattr(slot, "value"):
                with suppress(Exception):
                    out[i] = slot.value  # type: ignore[attr-defined]
        return out

    def _restore_hook_values(hs: list[Any], snap: dict[int, Any]) -> None:
        for i, v in snap.items():
            if i >= len(hs):
                continue
            slot = hs[i]
            if hasattr(slot, "value"):
                with suppress(Exception):
                    slot.value = v  # type: ignore[attr-defined]

        # If render-phase updates were applied during this attempt before suspension,
        # some hooks record a base value to restore.
        for slot in hs:
            base = getattr(slot, "_render_phase_base", None)
            if base is not None and hasattr(slot, "value"):
                with suppress(Exception):
                    slot.value = base  # type: ignore[attr-defined]
                with suppress(Exception):
                    slot._render_phase_base = None

    def _discard_render_phase_pending(hs: list[Any]) -> None:
        for slot in hs:
            pending = getattr(slot, "pending", None)
            if not isinstance(pending, list) or not pending:
                continue
            keep = [u for u in pending if not bool(getattr(u, "render_phase", False))]
            pending[:] = keep

    while True:
        attempt += 1
        if attempt > max_restarts:
            raise HookError("Too many re-renders. The number of renders has exceeded the limit.")

        prev_hook_len = len(hooks)

        # For render-phase restarts, we must discard effects scheduled in aborted attempts.
        ins_len = len(scheduled_insertion_effects or [])
        lay_len = len(scheduled_layout_effects or [])
        pas_len = len(scheduled_passive_effects or [])
        sl_len = len(scheduled_strict_layout_effects or [])
        sp_len = len(scheduled_strict_passive_effects or [])

        initial_hooks_len, pending_marks = _snapshot_pending_lengths(hooks)
        value_snap = _snapshot_hook_values(hooks)

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
            strict_remaining_mount_pass=strict_remaining_mount_pass,
            from_class_render=from_class_render,
            legacy_context=legacy_context,
        )
        try:
            if inspect.iscoroutinefunction(fn):
                assert _current_frame is not None
                _current_frame.async_component = True
                try:
                    from ryact_testkit.warnings import emit_warning as _emit_warning

                    _emit_warning(
                        "warn if async client component calls a hook",
                        stacklevel=3,
                    )
                except Exception:
                    pass
        except Exception:
            pass
        ok = False
        result: Any = None
        frame = None
        try:
            result = fn(**props)
            ok = True
            # If userland catches a suspension thrown by `use()` and continues rendering,
            # warn. React's dispatcher is unset in this scenario; we approximate by tracking
            # whether a suspension happened during this attempt but the render returned.
            try:
                frame_now = _current_frame
                if frame_now is not None and getattr(frame_now, "suspended", False):
                    from ryact_testkit.warnings import emit_warning as _emit_warning

                    _emit_warning(
                        "warns if use(promise) is wrapped with try/catch block",
                        stacklevel=3,
                    )
            except Exception:
                pass
            if inspect.isawaitable(result):
                try:
                    # Avoid leaking "coroutine was never awaited" warnings in tests.
                    close = getattr(result, "close", None)
                    if callable(close):
                        close()
                except Exception:
                    pass
                raise RuntimeError("Async component functions are not supported outside Suspense.")
        except Suspend:
            # If the component suspended, discard render-phase state updates from this attempt.
            _rollback_pending_lengths(hooks, initial_hooks_len, pending_marks)
            _restore_hook_values(hooks, value_snap)
            _discard_render_phase_pending(hooks)
            raise
        finally:
            frame = _current_frame
            try:
                if ok and frame is not None and not frame.is_mount and len(frame.hooks) != prev_hook_len:
                    if len(frame.hooks) < prev_hook_len:
                        raise HookError("Rendered fewer hooks than during the previous render.")
                    raise HookError("Rendered more hooks than during the previous render.")
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
            from_class_render=True,
        )
    if isinstance(component_type, type):
        raise TypeError(f"Expected a function component or a subclass of Component, got class {component_type!r}")
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
