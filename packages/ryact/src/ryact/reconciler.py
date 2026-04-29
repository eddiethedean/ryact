from __future__ import annotations

import warnings
from collections.abc import Callable, Mapping
from contextlib import suppress
from dataclasses import dataclass, field
from typing import Any, Optional, cast

from schedulyr import (
    IDLE_PRIORITY,
    IMMEDIATE_PRIORITY,
    LOW_PRIORITY,
    NORMAL_PRIORITY,
    USER_BLOCKING_PRIORITY,
    Scheduler,
)

from .component import Component
from .context import Context
from .devtools import component_stack_from_fiber
from .element import (
    Element,
    coerce_top_level_render_result,
    create_element,
    props_for_component_render,
)
from .hooks import (
    _current_commit_phase,
    _is_class_component,
    _render_with_hooks,
    _set_commit_context,
    _tag_effect,
)
from .wrappers import ForwardRefType, MemoType, shallow_equal_props


@dataclass
class Lane:
    """
    Minimal lanes/priorities scaffold.

    This exists to mirror the conceptual model in React's reconciler;
    real behavior will be driven by translated tests as they land.
    """

    name: str
    priority: int


SYNC_LANE = Lane("sync", 1)

# DEV StrictMode: while True, class `render()` side effects that schedule updates are ignored
# for the intentionally discarded first render (mirrors React's suppressed render pass).
_strict_discard_class_render: list[bool] = [False]


def _dev_strict_precommit_double(root: Any, strict: bool) -> bool:
    """DEV-only: double class precommit work under concurrent StrictMode or legacy+StrictMode."""
    from .dev import is_dev

    if not is_dev():
        return False
    if strict:
        return True
    try:
        return int(getattr(root, "_legacy_strict_dev_precommit_depth", 0)) > 0
    except Exception:
        return False


USER_BLOCKING_LANE = Lane("user-blocking", 2)
DEFAULT_LANE = Lane("default", 2)
TRANSITION_LANE = Lane("transition", 3)
LOW_LANE = Lane("low", 3)
IDLE_LANE = Lane("idle", 3)


def lane_to_scheduler_priority(lane: Lane) -> int:
    """
    Map reconciler lanes to ``schedulyr`` numeric priorities (lower = sooner).

    Used only with the default cooperative :class:`schedulyr.scheduler.Scheduler` on
    :attr:`Root.scheduler`. Browser / fork harnesses (MessageChannel,
    ``setImmediate``, ``postTask``, etc.) are **not** wired through the reconciler;
    see ``packages/schedulyr/SCHEDULER_ENTRYPOINTS.md``.
    """
    if lane.name == "sync":
        return IMMEDIATE_PRIORITY
    if lane.name == "user-blocking":
        return USER_BLOCKING_PRIORITY
    if lane.name == "transition":
        return LOW_PRIORITY
    if lane.name == "idle":
        return IDLE_PRIORITY
    if lane.name == "low":
        return LOW_PRIORITY
    return NORMAL_PRIORITY


@dataclass
class Fiber:
    type: Any
    key: str | None
    pending_props: dict[str, Any]
    memoized_props: dict[str, Any] = field(default_factory=dict)
    state_node: Any = None

    parent: Fiber | None = None
    child: Fiber | None = None
    sibling: Fiber | None = None

    hooks: list[Any] = field(default_factory=list)
    alternate: Fiber | None = None
    index: int = 0
    memoized_snapshot: Any = None


def _iter_children(fiber: Fiber | None) -> list[Fiber]:
    out: list[Fiber] = []
    c = fiber.child if fiber is not None else None
    while c is not None:
        out.append(c)
        c = c.sibling
    return out


def _reconcile_child(
    parent: Fiber,
    *,
    index: int,
    type_: Any,
    key: str | None,
    pending_props: dict[str, Any],
) -> Fiber:
    alt_parent = parent.alternate
    alt_children = _iter_children(alt_parent)
    alt: Fiber | None = None
    if key is not None:
        for c in alt_children:
            if c.key == key and c.type == type_:
                alt = c
                break
    else:
        # When reconciling unkeyed children, prefer a stable identity-path match if available.
        # This avoids mis-reconciling when the alternate child list has "holes" (e.g. None)
        # that were not materialized into fibers.
        parent_path = getattr(parent, "_identity_path", None)
        if isinstance(parent_path, str) and parent_path:
            expected = f"{parent_path}.{index}"
            for c in alt_children:
                if (
                    c.key is None
                    and c.type == type_
                    and getattr(c, "_identity_path", None) == expected
                ):
                    alt = c
                    break
            # Fallback: wrapper nodes (StrictMode/Offscreen/Suspense/etc.) may intentionally
            # use non-index-based identity paths for their *own* fibers (e.g. "0.sm", "0.o").
            # Reuse by index only for those wrapper-style identity paths; do NOT do this for
            # regular index-based identities because holes (e.g. [A, None, C]) would shift
            # `alt_children` and cause incorrect reuse.
            if alt is None and index < len(alt_children):
                c = alt_children[index]
                if c.key is None and c.type == type_:
                    ident = getattr(c, "_identity_path", None)
                    is_index_identity = False
                    if isinstance(ident, str) and ident.startswith(parent_path + "."):
                        suffix = ident[len(parent_path) + 1 :]
                        is_index_identity = suffix.isdigit()
                    if not is_index_identity:
                        alt = c
        else:
            if index < len(alt_children):
                c = alt_children[index]
                if c.key is None and c.type == type_:
                    alt = c
    if alt is not None:
        wip = Fiber(type=type_, key=key, pending_props=pending_props, alternate=alt, index=index)
        wip.hooks = list(alt.hooks)
    else:
        wip = Fiber(type=type_, key=key, pending_props=pending_props, index=index)
    wip.parent = parent
    return wip


def reconcile_key_first_indices(old_keys: list[str], new_keys: list[str]) -> list[dict[str, Any]]:
    """
    Compute a minimal key-first op list (insert/move/delete) by index.

    This is a tiny subset of React's child reconciliation, intended for the noop host.
    """
    old_index_by_key = {k: i for i, k in enumerate(old_keys)}
    used_old: set[str] = set()
    ops: list[dict[str, Any]] = []

    for new_i, k in enumerate(new_keys):
        if k in old_index_by_key and k not in used_old:
            old_i = old_index_by_key[k]
            used_old.add(k)
            if old_i != new_i:
                ops.append({"op": "move", "from": old_i, "to": new_i})
        else:
            ops.append({"op": "insert", "to": new_i, "key": k})

    for old_i, k in enumerate(old_keys):
        if k not in used_old:
            ops.append({"op": "delete", "from": old_i, "key": k})

    return ops


@dataclass
class Root:
    container_info: Any
    current: Fiber | None = None
    pending_updates: list[Update] = field(default_factory=list)
    scheduler: Optional[Scheduler] = None
    _flush_task_id: int | None = None
    _flush_priority: int | None = None
    _commit_fn: Callable[[Any], Any] | None = None
    _current_lane: Lane = field(default_factory=lambda: DEFAULT_LANE)
    _last_element: Element | None = None


@dataclass
class Update:
    lane: Lane
    payload: Any


def create_root(container_info: Any, scheduler: Optional[Scheduler] = None) -> Root:
    """
    Create a root. When ``scheduler`` is set, deferred updates use the default
    :class:`schedulyr.scheduler.Scheduler` only (not ``BrowserSchedulerHarness``
    or other hosts).
    """
    return Root(container_info=container_info, scheduler=scheduler)


def bind_commit(root: Root, commit: Callable[[Any], Any]) -> None:
    """
    Store the host commit callback before ``schedule_update_on_root`` when
    ``root.scheduler`` is set.

    The scheduled flush is a ``Scheduler.schedule_callback`` task (see
    ``schedule_update_on_root``); when it runs, it calls :func:`perform_work` with
    this ``commit`` callback.
    """

    root._commit_fn = commit


def schedule_update_on_root(root: Root, update: Update) -> None:
    """
    Queue an update. If ``root.scheduler`` is ``None``, only appends to
    ``pending_updates`` (synchronous callers flush elsewhere).

    If a ``Scheduler`` is set: requires :func:`bind_commit` first, then
    **coalesces** flushes into a single scheduled task.

    Coalescing policy:
    - Do not schedule more than one flush at a time.
    - Never *downgrade* the scheduled flush priority. If a higher-urgency lane is
      scheduled while a flush is pending, cancel and reschedule at the higher
      priority; otherwise keep the existing flush.
    """
    root.pending_updates.append(update)
    if isinstance(update.payload, Element) or update.payload is None:
        root._last_element = update.payload
    if root.scheduler is None:
        return
    if root._commit_fn is None:
        raise RuntimeError(
            "bind_commit() must be called before schedule_update_on_root when root.scheduler is set"
        )
    desired_priority = lane_to_scheduler_priority(update.lane)
    if root._flush_task_id is not None:
        assert root._flush_priority is not None
        # Lower numeric priority means "more urgent" in schedulyr.
        if desired_priority >= root._flush_priority:
            return
        root.scheduler.cancel_callback(root._flush_task_id)
        root._flush_task_id = None
        root._flush_priority = None

    def flush() -> Callable[[], Any] | None:
        root._flush_task_id = None
        root._flush_priority = None
        fn = root._commit_fn
        if fn is not None and root.pending_updates:
            perform_work(root, fn)
        # Return a continuation if more work was queued while flushing.
        if fn is not None and root.pending_updates:
            return flush
        return None

    root._flush_task_id = root.scheduler.schedule_callback(desired_priority, flush, delay_ms=0)
    root._flush_priority = desired_priority


def perform_work(root: Root, render: Callable[[Any], Any]) -> None:
    """
    Extremely early commit model:
    - Process all queued updates in priority order
    - For now, the payload is the root Element to render
    - Delegates actual host rendering to the provided `render` callback
    """

    if not root.pending_updates:
        return

    updates = list(root.pending_updates)
    root.pending_updates.clear()

    # For deferred (scheduler-attached) roots we intentionally keep an early
    # “coalesced commit” model: schedule/priority chooses *when* the flush runs;
    # the flush commits the most recently scheduled payload.
    if root.scheduler is not None:
        last = updates[-1]
        root._current_lane = last.lane
        if isinstance(last.payload, Element) or last.payload is None:
            root._last_element = last.payload
        render(last.payload)
        return

    # Synchronous roots: deterministic flush order by lane priority, then insertion order.
    # (Class setState can queue multiple root updates; the reconciler applies at most one
    # eligible class patch per render; hook pending updates batch inside one render via hooks.py.)
    updates.sort(key=lambda u: u.lane.priority)
    for i, u in enumerate(updates):
        root._current_lane = u.lane
        if isinstance(u.payload, Element) or u.payload is None:
            root._last_element = u.payload
        try:
            render(u.payload)
        except _NoopYield as y:
            # Pause flush: re-queue remaining work (including current update) and return.
            y._ryact_no_root_retry = True  # type: ignore[attr-defined]
            root.pending_updates[:0] = updates[i:]
            return


Renderable = Element | str | int | float | None


class _NoopYield(BaseException):
    """Internal signal used by noop roots to pause work and resume on the next flush."""


def _set_fiber_identity_path(fiber: Fiber, identity_path: str) -> None:
    try:
        fiber._identity_path = identity_path  # type: ignore[attr-defined]
    except Exception:
        pass


def _strict_lifecycle_record(root: Root, *, lifecycle: str, component_name: str) -> None:
    """
    Track StrictMode lifecycle warnings and coalesce by lifecycle name.

    We record during render and emit as commit callbacks so the warning capture
    harness sees them deterministically.
    """
    pending = getattr(root, "_strict_lifecycle_warnings_pending", None)
    if not isinstance(pending, dict):
        pending = {}
        with suppress(Exception):
            root._strict_lifecycle_warnings_pending = pending  # type: ignore[attr-defined]
    names = pending.get(lifecycle)
    if not isinstance(names, set):
        names = set()
        pending[lifecycle] = names
    names.add(component_name)


_LEGACY_CONTEXT_LINK = "https://react.dev/link/legacy-context"


def _strict_legacy_record(root: Root, *, component_name: str, kind: str) -> None:
    pl = getattr(root, "_strict_legacy_pending", None)
    if not isinstance(pl, list):
        pl = []
        with suppress(Exception):
            root._strict_legacy_pending = pl  # type: ignore[attr-defined]
    pl.append((component_name, kind))


def _strict_legacy_flush(root: Root) -> list[Callable[[], None]]:
    pending = getattr(root, "_strict_legacy_pending", None)
    if not isinstance(pending, list) or not pending:
        return []
    emitted_tree = getattr(root, "_strict_legacy_emitted_names", None)
    if not isinstance(emitted_tree, set):
        emitted_tree = set()
        root._strict_legacy_emitted_names = emitted_tree  # type: ignore[attr-defined]

    names_in_tree = {name for name, _ in pending if isinstance(name, str)}
    new_names = names_in_tree - emitted_tree
    if not new_names:
        return []

    kind_rank = {"provider": 0, "class_consumer": 1, "fn_consumer": 2}
    normalized = [
        (n, k)
        for n, k in pending
        if isinstance(n, str) and isinstance(k, str) and k in kind_rank
    ]
    ordered = sorted(normalized, key=lambda t: (kind_rank[t[1]], t[0]))

    callbacks: list[Callable[[], None]] = []
    for name, kind in ordered:
        if not isinstance(name, str) or name not in new_names:
            continue
        if kind == "provider":
            body = (
                f"{name} uses the legacy childContextTypes API which will soon be removed. "
                f"Use create_context() instead. ({_LEGACY_CONTEXT_LINK})"
            )
        elif kind == "class_consumer":
            body = (
                f"{name} uses the legacy contextTypes API which will soon be removed. "
                f"Use create_context() with static contextType instead. ({_LEGACY_CONTEXT_LINK})"
            )
        else:
            body = (
                f"{name} uses the legacy contextTypes API which will be removed soon. "
                f"Use create_context() with use_context() instead. ({_LEGACY_CONTEXT_LINK})"
            )

        def _warn_one(msg: str = body) -> None:
            warnings.warn(msg, RuntimeWarning, stacklevel=2)

        callbacks.append(_warn_one)

    agg_list = ", ".join(sorted(names_in_tree))
    agg_body = (
        "Legacy context API has been detected within a strict-mode tree.\n\n"
        "The old API will be supported in all 16.x releases, but applications "
        "using it should migrate to the new version.\n\n"
        f"Please update the following components: {agg_list}\n\n"
        f"Learn more about this warning here: {_LEGACY_CONTEXT_LINK}"
    )

    def _warn_agg(msg: str = agg_body) -> None:
        warnings.warn(msg, RuntimeWarning, stacklevel=2)

    callbacks.append(_warn_agg)
    emitted_tree.update(names_in_tree)
    return callbacks


def _strict_lifecycle_flush(root: Root) -> list[Callable[[], None]]:
    pending = getattr(root, "_strict_lifecycle_warnings_pending", None)
    if not isinstance(pending, dict) or not pending:
        return []
    emitted = getattr(root, "_strict_lifecycle_warnings_emitted", None)
    if not isinstance(emitted, dict):
        emitted = {}
        with suppress(Exception):
            root._strict_lifecycle_warnings_emitted = emitted  # type: ignore[attr-defined]
    # Clear pending for the next render.
    with suppress(Exception):
        root._strict_lifecycle_warnings_pending = {}  # type: ignore[attr-defined]

    callbacks: list[Callable[[], None]] = []
    for lifecycle, names in pending.items():
        if not isinstance(lifecycle, str) or not isinstance(names, set) or not names:
            continue
        prev = emitted.get(lifecycle)
        if not isinstance(prev, set):
            prev = set()
            emitted[lifecycle] = prev
        new_names = sorted(n for n in names if n not in prev)
        if not new_names:
            continue
        prev.update(new_names)

        def _warn(lc: str = lifecycle, comps: list[str] = new_names) -> None:
            msg = f"StrictMode unsafe lifecycle `{lc}` was found. Components: {', '.join(comps)}."
            warnings.warn(msg, RuntimeWarning, stacklevel=2)

        callbacks.append(_warn)
    return callbacks


def _clone_fiber_subtree_for_reuse(prev: Fiber, *, parent: Fiber | None = None) -> Fiber:
    """
    Clone a previously committed fiber subtree into a new WIP tree, preserving
    alternate links so unmount detection considers it reused.

    Used by the noop Suspense model to keep the prior primary tree mounted (hidden)
    when a boundary re-suspends and switches to fallback.
    """
    pending = dict(getattr(prev, "memoized_props", None) or getattr(prev, "pending_props", None) or {})
    wip = Fiber(type=prev.type, key=prev.key, pending_props=pending, alternate=prev, index=prev.index)
    wip.memoized_props = dict(getattr(prev, "memoized_props", {}) or {})
    wip.memoized_snapshot = getattr(prev, "memoized_snapshot", None)
    wip.state_node = getattr(prev, "state_node", None)
    # Copy hook slots so effect cleanups remain associated with the preserved instance.
    wip.hooks = list(getattr(prev, "hooks", []) or [])
    wip.parent = parent
    ident = getattr(prev, "_identity_path", None)
    if isinstance(ident, str):
        _set_fiber_identity_path(wip, ident)

    prev_child = getattr(prev, "child", None)
    last: Fiber | None = None
    while prev_child is not None:
        cloned = _clone_fiber_subtree_for_reuse(prev_child, parent=wip)
        if last is None:
            wip.child = cloned
        else:
            last.sibling = cloned
        last = cloned
        prev_child = getattr(prev_child, "sibling", None)
    return wip


def _child_identity_path(parent_path: str, index: int, child: Any) -> str:
    try:
        k = getattr(child, "key", None)
    except Exception:
        k = None
    if isinstance(k, str) and k:
        # Key is the stable id for reconciler + noop unmount diffing; do not encode `index`
        # or a keyed fiber that moves (e.g. first -> second child) is treated as unmounted+new.
        return f"{parent_path}.$k${k}"
    return f"{parent_path}.{index}"


@dataclass
class NoopWork:
    snapshot: Any
    insertion_effects: list[Callable[[], None]]
    layout_effects: list[Callable[[], None]]
    passive_effects: list[Callable[[], None]]
    strict_layout_effects: list[Callable[[], None]] = field(default_factory=list)
    strict_passive_effects: list[Callable[[], None]] = field(default_factory=list)
    commit_callbacks: list[Callable[[], None]] = field(default_factory=list)
    finished_work: Fiber | None = None


def _apply_queued_class_state_for_sync_render(
    instance: Any,
    root: Any,
    *,
    strict: bool,
) -> None:
    """
    Apply all eligible queued setState/replaceState updates so a synchronous
    ``render()`` (e.g. right after componentDidCatch) sees updated state.
    """
    from .dev import is_dev

    pending = getattr(instance, "_pending_state_updates", None)
    if not isinstance(pending, list) or not pending:
        return
    visible_pri = root._current_lane.priority
    remaining: list[Any] = []
    for item in pending:
        if not (
            isinstance(item, tuple)
            and len(item) in (2, 3)
            and isinstance(item[0], Lane)
        ):
            continue
        lane = item[0]
        patch = item[1]
        replace = bool(item[2]) if len(item) == 3 else False
        if lane.priority <= visible_pri:
            if callable(patch):
                next_patch = patch(instance.state, instance.props)
                if strict and is_dev():
                    try:
                        _ = patch(instance.state, instance.props)
                    except Exception:
                        pass
                if isinstance(next_patch, dict):
                    if replace:
                        instance._state = dict(next_patch)  # type: ignore[attr-defined]
                    else:
                        instance._state.update(next_patch)  # type: ignore[attr-defined]
            elif isinstance(patch, dict):
                if replace:
                    instance._state = dict(patch)  # type: ignore[attr-defined]
                else:
                    instance._state.update(patch)  # type: ignore[attr-defined]
        else:
            remaining.append((lane, patch, replace))
    pending[:] = remaining


def _render_noop(
    node: Renderable,
    root: Root,
    identity_path: str,
    next_id: Callable[[], str],
    *,
    parent_fiber: Fiber,
    index: int,
    strict: bool = False,
    visible: bool = True,
    reappearing: bool = False,
) -> NoopWork:
    """
    Deterministic snapshot renderer used by test harnesses (e.g. ryact-testkit’s noop renderer).

    This is intentionally minimal and exists to support Milestone 3 test translation work.
    DOM/native renderers remain separate.
    """
    if node is None:
        return NoopWork(
            snapshot=None,
            insertion_effects=[],
            layout_effects=[],
            passive_effects=[],
            strict_layout_effects=[],
            strict_passive_effects=[],
            commit_callbacks=[],
            finished_work=None,
        )
    if isinstance(node, (str, int, float)):
        return NoopWork(
            snapshot=str(node),
            insertion_effects=[],
            layout_effects=[],
            passive_effects=[],
            strict_layout_effects=[],
            strict_passive_effects=[],
            commit_callbacks=[],
            finished_work=None,
        )
    if not isinstance(node, Element):
        raise TypeError(f"Unsupported node type: {type(node)!r}")

    # Minimal interruption hook: allow tests to configure a coarse work budget.
    try:
        budget = int(getattr(root, "_yield_after_nodes", 0) or 0)
    except Exception:
        budget = 0
    if budget > 0:
        try:
            seen = int(getattr(root, "_yield_seen_nodes", 0) or 0)
        except Exception:
            seen = 0
        seen += 1
        try:
            root._yield_seen_nodes = seen  # type: ignore[attr-defined]
        except Exception:
            pass
        if seen >= budget:
            try:
                root._yield_seen_nodes = 0  # type: ignore[attr-defined]
            except Exception:
                pass
            y = _NoopYield()
            try:
                y._ryact_no_root_retry = True  # type: ignore[attr-defined]
            except Exception:
                pass
            raise y

    # Host element: string tag
    if isinstance(node.type, str):
        fiber = _reconcile_child(
            parent_fiber,
            index=index,
            type_=node.type,
            key=node.key,
            pending_props={**dict(node.props), "__ref__": node.ref},
        )
        _set_fiber_identity_path(fiber, identity_path)
        if node.type == "__offscreen__":
            # Minimal Offscreen/Activity-like wrapper for noop host.
            mode = None
            if isinstance(node.props, Mapping):
                mode = node.props.get("mode")
                if node.props.get("__warn_hidden__"):
                    stack = component_stack_from_fiber(fiber)
                    msg = "Passing `hidden` is unsupported; use `mode='hidden'` instead."
                    if stack:
                        msg = msg + "\n\n" + stack
                    warnings.warn(msg, RuntimeWarning, stacklevel=2)
            is_hidden = mode == "hidden"
            prev_mode = None
            if fiber.alternate is not None:
                prev_props = getattr(fiber.alternate, "memoized_props", None) or getattr(
                    fiber.alternate, "pending_props", None
                )
                if isinstance(prev_props, dict):
                    prev_mode = prev_props.get("mode")
            was_hidden = prev_mode == "hidden"
            children = node.props.get("children", ()) if isinstance(node.props, Mapping) else ()
            child = children[0] if children else None
            try:
                child_work = _render_noop(
                    child,
                    root,
                    f"{identity_path}.o",
                    next_id,
                    parent_fiber=fiber,
                    index=0,
                    strict=strict,
                    visible=visible and (not is_hidden),
                    reappearing=reappearing or (was_hidden and not is_hidden),
                )
            except Exception:
                # Hidden trees should not affect the visible UI; treat errors as contained.
                if is_hidden or not visible:
                    child_work = NoopWork(
                        snapshot=None,
                        insertion_effects=[],
                        layout_effects=[],
                        passive_effects=[],
                        commit_callbacks=[],
                        finished_work=None,
                    )
                else:
                    raise
            fiber.child = child_work.finished_work
            if is_hidden or not visible:
                # Hidden subtrees are prerendered for identity but do not commit output/effects.
                return NoopWork(
                    snapshot=None,
                    insertion_effects=[],
                    layout_effects=[],
                    passive_effects=[],
                    commit_callbacks=[],
                    finished_work=fiber,
                )
            return NoopWork(
                snapshot=child_work.snapshot,
                insertion_effects=child_work.insertion_effects,
                layout_effects=child_work.layout_effects,
                passive_effects=child_work.passive_effects,
                strict_layout_effects=child_work.strict_layout_effects,
                strict_passive_effects=child_work.strict_passive_effects,
                commit_callbacks=child_work.commit_callbacks,
                finished_work=fiber,
            )
        if node.type == "__context_provider__":
            fiber = _reconcile_child(
                parent_fiber,
                index=index,
                type_="__context_provider__",
                key=node.key,
                pending_props=dict(node.props),
            )
            _set_fiber_identity_path(fiber, identity_path)
            props = node.props if isinstance(node.props, Mapping) else {}
            ctx_obj = props.get("context")
            val = props.get("value")
            children = props.get("children", ())
            child = children[0] if children else None
            prev: Any = None
            restore = isinstance(ctx_obj, Context)
            if restore:
                prev = ctx_obj._current_value
                ctx_obj._current_value = val
            try:
                child_work = _render_noop(
                    child,
                    root,
                    f"{identity_path}.ctx",
                    next_id,
                    parent_fiber=fiber,
                    index=0,
                    strict=strict,
                    visible=visible,
                    reappearing=reappearing,
                )
            finally:
                if restore:
                    ctx_obj._current_value = prev
            fiber.child = child_work.finished_work
            return NoopWork(
                snapshot=child_work.snapshot,
                insertion_effects=child_work.insertion_effects,
                layout_effects=child_work.layout_effects,
                passive_effects=child_work.passive_effects,
                strict_layout_effects=child_work.strict_layout_effects,
                strict_passive_effects=child_work.strict_passive_effects,
                commit_callbacks=child_work.commit_callbacks,
                finished_work=fiber,
            )
        if node.type in ("__js_subtree__", "__py_subtree__"):
            runner = getattr(root.container_info, "interop_runner", None)
            if runner is None:
                raise RuntimeError(
                    "Interop boundary encountered but no interop_runner is configured "
                    "on the noop root."
                )
            boundary_id = identity_path
            props = node.props.get("props") if isinstance(node.props, Mapping) else None
            children = node.props.get("children", ()) if isinstance(node.props, Mapping) else ()
            if node.type == "__js_subtree__":
                module_id = str(node.props.get("module_id"))
                export = str(node.props.get("export", "default"))
                rendered = runner.render_js(
                    module_id=module_id,
                    export=export,
                    props=props,
                    children=children,
                    boundary_id=boundary_id,
                )
            else:
                component_id = str(node.props.get("component_id"))
                rendered = runner.render_py(
                    component_id=component_id,
                    props=props,
                    children=children,
                    boundary_id=boundary_id,
                )
            work = _render_noop(
                cast(Renderable, rendered),
                root,
                f"{identity_path}.interop",
                next_id,
                parent_fiber=fiber,
                index=0,
                strict=strict,
                visible=visible,
                reappearing=reappearing,
            )
            fiber.child = work.finished_work
            return NoopWork(
                snapshot=work.snapshot,
                insertion_effects=work.insertion_effects,
                layout_effects=work.layout_effects,
                passive_effects=work.passive_effects,
                strict_layout_effects=work.strict_layout_effects,
                strict_passive_effects=work.strict_passive_effects,
                commit_callbacks=work.commit_callbacks,
                finished_work=fiber,
            )
        if node.type == "__fragment__":
            children = node.props.get("children", ())
            rendered_children: list[Any] = []
            insertion_effects: list[Callable[[], None]] = []
            layout_effects: list[Callable[[], None]] = []
            passive_effects: list[Callable[[], None]] = []
            strict_layout_effects: list[Callable[[], None]] = []
            strict_passive_effects: list[Callable[[], None]] = []
            commit_callbacks: list[Callable[[], None]] = []
            prev_child: Fiber | None = None
            for i, c in enumerate(children):
                w = _render_noop(
                    c,
                    root,
                    _child_identity_path(identity_path, i, c),
                    next_id,
                    parent_fiber=fiber,
                    index=i,
                    strict=strict,
                    visible=visible,
                    reappearing=reappearing,
                )
                if isinstance(w.snapshot, list):
                    rendered_children.extend(w.snapshot)
                else:
                    rendered_children.append(w.snapshot)
                insertion_effects.extend(w.insertion_effects)
                layout_effects.extend(w.layout_effects)
                passive_effects.extend(w.passive_effects)
                strict_layout_effects.extend(w.strict_layout_effects)
                strict_passive_effects.extend(w.strict_passive_effects)
                commit_callbacks.extend(w.commit_callbacks)
                if w.finished_work is not None:
                    if prev_child is None:
                        fiber.child = w.finished_work
                    else:
                        prev_child.sibling = w.finished_work
                    prev_child = w.finished_work
            return NoopWork(
                snapshot=rendered_children,
                insertion_effects=insertion_effects,
                layout_effects=layout_effects,
                passive_effects=passive_effects,
                strict_layout_effects=strict_layout_effects,
                strict_passive_effects=strict_passive_effects,
                commit_callbacks=commit_callbacks,
                finished_work=fiber,
            )
        if node.type == "__suspense_list__":
            from .concurrent import Suspend

            children = node.props.get("children", ())
            child = children[0] if children else None
            reveal_order = node.props.get("reveal_order") or "forwards"
            tail = node.props.get("tail") or "hidden"

            list_children: tuple[Any, ...] = ()
            if isinstance(child, Element) and isinstance(getattr(child, "props", None), Mapping):
                if child.type == "__fragment__":
                    list_children = tuple(child.props.get("children", ()))
            elif isinstance(child, (list, tuple)):
                list_children = tuple(child)
            else:
                list_children = (child,)

            if reveal_order not in ("forwards", "backwards", "together"):
                reveal_order = "forwards"
            if tail not in ("hidden", "collapsed"):
                tail = "hidden"

            if reveal_order == "backwards":
                ordered = list(reversed(list_children))
            else:
                ordered = list(list_children)

            rendered_children: list[Any] = []
            insertion_effects: list[Callable[[], None]] = []
            layout_effects: list[Callable[[], None]] = []
            passive_effects: list[Callable[[], None]] = []
            strict_layout_effects: list[Callable[[], None]] = []
            strict_passive_effects: list[Callable[[], None]] = []
            commit_callbacks: list[Callable[[], None]] = []
            prev_child: Fiber | None = None

            hit_suspension = False
            for i, c in enumerate(ordered):
                if hit_suspension and tail == "hidden":
                    continue

                if isinstance(c, Element) and c.type == "__suspense__":
                    fallback = c.props.get("fallback")
                    s_children = c.props.get("children", ())
                    primary = s_children[0] if s_children else None
                    try:
                        w = _render_noop(
                            primary,
                            root,
                            _child_identity_path(identity_path, i, primary),
                            next_id,
                            parent_fiber=fiber,
                            index=i,
                            strict=strict,
                            visible=visible,
                            reappearing=reappearing,
                        )
                        snap = w.snapshot
                    except Suspend:
                        hit_suspension = True
                        w = _render_noop(
                            fallback,
                            root,
                            _child_identity_path(identity_path, i, fallback),
                            next_id,
                            parent_fiber=fiber,
                            index=i,
                            strict=strict,
                            visible=visible,
                            reappearing=reappearing,
                        )
                        snap = w.snapshot
                else:
                    w = _render_noop(
                        c,
                        root,
                        _child_identity_path(identity_path, i, c),
                        next_id,
                        parent_fiber=fiber,
                        index=i,
                        strict=strict,
                        visible=visible,
                        reappearing=reappearing,
                    )
                    snap = w.snapshot

                if isinstance(snap, list):
                    rendered_children.extend(snap)
                else:
                    rendered_children.append(snap)
                insertion_effects.extend(w.insertion_effects)
                layout_effects.extend(w.layout_effects)
                passive_effects.extend(w.passive_effects)
                strict_layout_effects.extend(w.strict_layout_effects)
                strict_passive_effects.extend(w.strict_passive_effects)
                commit_callbacks.extend(w.commit_callbacks)
                if w.finished_work is not None:
                    if prev_child is None:
                        fiber.child = w.finished_work
                    else:
                        prev_child.sibling = w.finished_work
                    prev_child = w.finished_work

            if reveal_order == "backwards":
                rendered_children = list(reversed(rendered_children))

            return NoopWork(
                snapshot=rendered_children,
                insertion_effects=insertion_effects,
                layout_effects=layout_effects,
                passive_effects=passive_effects,
                strict_layout_effects=strict_layout_effects,
                strict_passive_effects=strict_passive_effects,
                commit_callbacks=commit_callbacks,
                finished_work=fiber,
            )
        if node.type == "__profiler__":
            children = node.props.get("children", ())
            child = children[0] if children else None
            pid = str(node.props.get("id", ""))
            on_render = node.props.get("on_render")

            work = _render_noop(
                child,
                root,
                _child_identity_path(f"{identity_path}.p", 0, child),
                next_id,
                parent_fiber=fiber,
                index=0,
                strict=strict,
                visible=visible,
                reappearing=reappearing,
            )
            fiber.child = work.finished_work

            phase = "mount" if getattr(fiber, "alternate", None) is None else "update"

            commit_callbacks = list(work.commit_callbacks)

            if callable(on_render):
                def _cb() -> None:
                    # Deterministic placeholder numbers (Phase 6 first slice).
                    on_render(pid, phase, 0.0, 0.0, 0.0, 0.0, ())

                commit_callbacks.append(_cb)

            return NoopWork(
                snapshot=work.snapshot,
                insertion_effects=work.insertion_effects,
                layout_effects=work.layout_effects,
                passive_effects=work.passive_effects,
                strict_layout_effects=work.strict_layout_effects,
                strict_passive_effects=work.strict_passive_effects,
                commit_callbacks=commit_callbacks,
                finished_work=fiber,
            )
        if node.type == "__strict_mode__":
            from .dev import is_dev

            children = node.props.get("children", ())
            child = children[0] if children else None
            legacy_mode = bool(getattr(root, "_legacy_mode", False))
            child_strict = (strict or is_dev()) and (not legacy_mode)
            if legacy_mode and is_dev():
                prev_depth = int(getattr(root, "_legacy_strict_dev_precommit_depth", 0))
                with suppress(Exception):
                    root._legacy_strict_dev_precommit_depth = prev_depth + 1  # type: ignore[attr-defined]
                try:
                    work = _render_noop(
                        child,
                        root,
                        f"{identity_path}.sm",
                        next_id,
                        parent_fiber=fiber,
                        index=0,
                        strict=child_strict,
                        visible=visible,
                        reappearing=reappearing,
                    )
                finally:
                    with suppress(Exception):
                        root._legacy_strict_dev_precommit_depth = prev_depth  # type: ignore[attr-defined]
            else:
                work = _render_noop(
                    child,
                    root,
                    f"{identity_path}.sm",
                    next_id,
                    parent_fiber=fiber,
                    index=0,
                    strict=child_strict,
                    visible=visible,
                    reappearing=reappearing,
                )
            fiber.child = work.finished_work
            return NoopWork(
                snapshot=work.snapshot,
                insertion_effects=work.insertion_effects,
                layout_effects=work.layout_effects,
                passive_effects=work.passive_effects,
                strict_layout_effects=work.strict_layout_effects,
                strict_passive_effects=work.strict_passive_effects,
                commit_callbacks=work.commit_callbacks,
                finished_work=fiber,
            )

        if node.type == "__suspense__":
            from .concurrent import Suspend

            fallback = node.props.get("fallback")
            children = node.props.get("children", ())
            try:
                # For now, expect a single child element.
                child = children[0] if children else None
                work = _render_noop(
                    child,
                    root,
                    _child_identity_path(f"{identity_path}.s", 0, child),
                    next_id,
                    parent_fiber=fiber,
                    index=0,
                    strict=strict,
                    visible=visible,
                    reappearing=reappearing,
                )
                fiber.child = work.finished_work
                return NoopWork(
                    snapshot=work.snapshot,
                    insertion_effects=work.insertion_effects,
                    layout_effects=work.layout_effects,
                    passive_effects=work.passive_effects,
                    strict_layout_effects=work.strict_layout_effects,
                    strict_passive_effects=work.strict_passive_effects,
                    commit_callbacks=work.commit_callbacks,
                    finished_work=fiber,
                )
            except Suspend as s:
                from .act import is_act_environment_enabled, is_in_act_scope

                def wake() -> None:
                    if root._last_element is None:
                        return
                    if is_act_environment_enabled() and not is_in_act_scope():
                        try:
                            warnings.warn(
                                "A Suspense ping was not wrapped in act(...).",
                                category=RuntimeWarning,
                                stacklevel=3,
                            )
                        except Exception:
                            pass
                    schedule_update_on_root(
                        root, Update(lane=DEFAULT_LANE, payload=root._last_element)
                    )

                # Hidden subtrees should not schedule wake work; they'll be retried on reveal.
                if visible:
                    s.thenable.then(wake)
                work = _render_noop(
                    fallback,
                    root,
                    f"{identity_path}.f",
                    next_id,
                    parent_fiber=fiber,
                    index=0,
                    strict=strict,
                    visible=visible,
                    reappearing=reappearing,
                )

                # If this boundary previously committed the primary tree, keep it mounted
                # (hidden) when switching to fallback on a re-suspend. This prevents unmount
                # cleanups from firing for the primary subtree, matching ReactNoop semantics.
                prev_primary: Fiber | None = None
                if fiber.alternate is not None:
                    cand = getattr(fiber.alternate, "child", None)
                    if cand is not None:
                        ident = getattr(cand, "_identity_path", None)
                        # Primary path uses `.s` while fallback uses `.f`.
                        if isinstance(ident, str) and ".f" not in ident:
                            prev_primary = cand
                if prev_primary is not None:
                    hidden = Fiber(
                        type="__offscreen__",
                        key=None,
                        pending_props={"mode": "hidden"},
                        alternate=None,
                        index=0,
                    )
                    _set_fiber_identity_path(hidden, f"{identity_path}.o")
                    hidden.parent = fiber
                    hidden.child = _clone_fiber_subtree_for_reuse(prev_primary, parent=hidden)
                    # Rendered fallback is the visible child; retained primary is hidden sibling.
                    hidden.sibling = work.finished_work
                    fiber.child = hidden
                else:
                    fiber.child = work.finished_work

                # DEV StrictMode: when a subtree suspends, React may attempt a best-effort
                # render of the primary tree to "prewarm" it. Model this by retrying the
                # child render once with `visible=False` (so it won't contribute output/effects),
                # and swallow any further Suspend.
                if strict and visible:
                    try:
                        _ = _render_noop(
                            child,
                            root,
                            _child_identity_path(f"{identity_path}.p", 0, child),
                            next_id,
                            parent_fiber=fiber,
                            index=0,
                            strict=strict,
                            visible=False,
                            reappearing=reappearing,
                        )
                    except Suspend:
                        pass
                return NoopWork(
                    snapshot=work.snapshot,
                    insertion_effects=work.insertion_effects,
                    layout_effects=work.layout_effects,
                    passive_effects=work.passive_effects,
                    strict_layout_effects=work.strict_layout_effects,
                    strict_passive_effects=work.strict_passive_effects,
                    commit_callbacks=work.commit_callbacks,
                    finished_work=fiber,
                )

        children = node.props.get("children", ())
        rendered_children2: list[Any] = []
        insertion_effects2: list[Callable[[], None]] = []
        layout_effects2: list[Callable[[], None]] = []
        passive_effects2: list[Callable[[], None]] = []
        strict_layout_effects2: list[Callable[[], None]] = []
        strict_passive_effects2: list[Callable[[], None]] = []
        commit_callbacks2: list[Callable[[], None]] = []
        prev_child2: Fiber | None = None
        for i, c in enumerate(children):
            w = _render_noop(
                c,
                root,
                _child_identity_path(identity_path, i, c),
                next_id,
                parent_fiber=fiber,
                index=i,
                strict=strict,
                visible=visible,
                reappearing=reappearing,
            )
            if isinstance(w.snapshot, list):
                rendered_children2.extend(w.snapshot)
            else:
                rendered_children2.append(w.snapshot)
            insertion_effects2.extend(w.insertion_effects)
            layout_effects2.extend(w.layout_effects)
            passive_effects2.extend(w.passive_effects)
            strict_layout_effects2.extend(w.strict_layout_effects)
            strict_passive_effects2.extend(w.strict_passive_effects)
            commit_callbacks2.extend(w.commit_callbacks)
            if w.finished_work is not None:
                if prev_child2 is None:
                    fiber.child = w.finished_work
                else:
                    prev_child2.sibling = w.finished_work
                prev_child2 = w.finished_work

        snap = {
            "type": node.type,
            "key": node.key,
            "props": {k: v for k, v in dict(node.props).items() if k != "children"},
            "children": rendered_children2,
        }
        return NoopWork(
            snapshot=snap,
            insertion_effects=insertion_effects2,
            layout_effects=layout_effects2,
            passive_effects=passive_effects2,
            strict_layout_effects=strict_layout_effects2,
            strict_passive_effects=strict_passive_effects2,
            commit_callbacks=commit_callbacks2,
            finished_work=fiber,
        )

    # Wrapper types: memo/forwardRef
    if isinstance(node.type, MemoType):
        fiber = _reconcile_child(
            parent_fiber,
            index=index,
            type_=node.type,
            key=node.key,
            pending_props=dict(node.props),
        )
        _set_fiber_identity_path(fiber, identity_path)
        prev_props = dict(fiber.alternate.memoized_props) if fiber.alternate is not None else None
        next_props = dict(node.props)
        compare = node.type.compare
        equal = False
        if prev_props is not None:
            if compare is not None:
                equal = bool(compare(prev_props, next_props))
            else:
                equal = shallow_equal_props(prev_props, next_props)

        def _subtree_context_changed(prev: Fiber | None) -> bool:
            from .context import Context

            if prev is None:
                return False
            stack: list[Fiber] = [prev]
            while stack:
                f = stack.pop()
                deps = getattr(f, "_context_deps", None)
                if isinstance(deps, dict):
                    for _, payload in deps.items():
                        if not (isinstance(payload, tuple) and len(payload) == 2):
                            continue
                        ctx, last_val = payload
                        if isinstance(ctx, Context):
                            try:
                                now = ctx._get()
                            except Exception:
                                continue
                            if now != last_val:
                                return True
                child = getattr(f, "child", None)
                if child is not None:
                    stack.append(child)
                sib = getattr(f, "sibling", None)
                if sib is not None:
                    stack.append(sib)
            return False

        if equal and fiber.alternate is not None:
            if _subtree_context_changed(getattr(fiber.alternate, "child", None)):
                equal = False
            else:
                # Bail out: reuse previous committed subtree.
                fiber.memoized_props = dict(fiber.alternate.memoized_props)
                fiber.memoized_snapshot = fiber.alternate.memoized_snapshot
                fiber.child = fiber.alternate.child
                return NoopWork(
                    snapshot=fiber.memoized_snapshot,
                    insertion_effects=[],
                    layout_effects=[],
                    passive_effects=[],
                    strict_layout_effects=[],
                    strict_passive_effects=[],
                    commit_callbacks=[],
                    finished_work=fiber,
                )

        rendered_memo = _render_noop(
            create_element(node.type.inner, next_props),
            root,
            f"{identity_path}.memo",
            next_id,
            parent_fiber=fiber,
            index=0,
            strict=strict,
            visible=visible,
            reappearing=reappearing,
        )
        fiber.memoized_props = next_props
        fiber.memoized_snapshot = rendered_memo.snapshot
        fiber.child = rendered_memo.finished_work
        return NoopWork(
            snapshot=rendered_memo.snapshot,
            insertion_effects=rendered_memo.insertion_effects,
            layout_effects=rendered_memo.layout_effects,
            passive_effects=rendered_memo.passive_effects,
            strict_layout_effects=rendered_memo.strict_layout_effects,
            strict_passive_effects=rendered_memo.strict_passive_effects,
            commit_callbacks=rendered_memo.commit_callbacks,
            finished_work=fiber,
        )

    if isinstance(node.type, ForwardRefType):
        fiber = _reconcile_child(
            parent_fiber,
            index=index,
            type_=node.type,
            key=node.key,
            pending_props=dict(node.props),
        )
        _set_fiber_identity_path(fiber, identity_path)
        if isinstance(node.ref, str):
            raise TypeError("String refs are not supported on ref-receiving components.")
        try:
            rendered = node.type.render(
                dict(props_for_component_render(node.type, node.props)), node.ref
            )
        except Exception as err:
            if "Component stack:" not in str(err):
                stack = component_stack_from_fiber(fiber)
                if stack:
                    err.args = (f"{err}\n\n{stack}",) + tuple(err.args[1:])
            raise
        work = _render_noop(
            cast(Renderable, rendered),
            root,
            f"{identity_path}.fr",
            next_id,
            parent_fiber=fiber,
            index=0,
            strict=strict,
            visible=visible,
            reappearing=reappearing,
        )
        fiber.memoized_props = dict(node.props)
        fiber.memoized_snapshot = work.snapshot
        fiber.child = work.finished_work
        return NoopWork(
            snapshot=work.snapshot,
            insertion_effects=work.insertion_effects,
            layout_effects=work.layout_effects,
            passive_effects=work.passive_effects,
            strict_layout_effects=work.strict_layout_effects,
            strict_passive_effects=work.strict_passive_effects,
            commit_callbacks=work.commit_callbacks,
            finished_work=fiber,
        )

    # Function/class component
    if callable(node.type):
        fiber = _reconcile_child(
            parent_fiber,
            index=index,
            type_=node.type,
            key=node.key,
            pending_props=dict(node.props),
        )
        _set_fiber_identity_path(fiber, identity_path)
        insertion_effects_fc: list[Callable[[], None]] = []
        layout_effects_fc: list[Callable[[], None]] = []
        passive_effects_fc: list[Callable[[], None]] = []
        strict_layout_effects_fc: list[Callable[[], None]] = []
        strict_passive_effects_fc: list[Callable[[], None]] = []
        commit_callbacks_fc: list[Callable[[], None]] = []

        def schedule_update(lane: Lane) -> None:
            schedule_update_on_root(root, Update(lane=lane, payload=root._last_element))

        rendered_comp: Any
        pre_dev_strict_dbl = _dev_strict_precommit_double(root, strict)
        if _is_class_component(node.type):
            from .concurrent import _with_update_lane
            from .dev import is_dev

            ct = getattr(node.type, "contextType", None)
            cts = getattr(node.type, "contextTypes", None)
            child_cts = getattr(node.type, "childContextTypes", None)
            get_child = getattr(node.type, "getChildContext", None)
            if is_dev() and ct is not None and cts is not None:
                stack = component_stack_from_fiber(fiber)
                msg = (
                    "A class component may not define both contextType and contextTypes."
                )
                if stack:
                    msg = msg + "\n\n" + stack
                warnings.warn(msg, RuntimeWarning, stacklevel=2)
            if is_dev() and child_cts is not None and not callable(get_child):
                stack = component_stack_from_fiber(fiber)
                msg = (
                    "childContextTypes is specified but getChildContext() is not defined."
                )
                if stack:
                    msg = msg + "\n\n" + stack
                warnings.warn(msg, RuntimeWarning, stacklevel=2)
            if is_dev() and ct is not None and not isinstance(ct, Context):
                stack = component_stack_from_fiber(fiber)
                msg = "Invalid contextType defined; expected a Context or None."
                if stack:
                    msg = msg + "\n\n" + stack
                warnings.warn(msg, RuntimeWarning, stacklevel=2)
            if pre_dev_strict_dbl:
                # Minimal StrictMode surface: coalesced warnings for legacy + UNSAFE lifecycles.
                comp_name = getattr(node.type, "__name__", "Component")
                for name in (
                    "UNSAFE_componentWillMount",
                    "UNSAFE_componentWillReceiveProps",
                    "UNSAFE_componentWillUpdate",
                    "componentWillMount",
                    "componentWillReceiveProps",
                    "componentWillUpdate",
                ):
                    if callable(getattr(node.type, name, None)):
                        _strict_lifecycle_record(root, lifecycle=name, component_name=comp_name)
                if child_cts is not None and callable(get_child):
                    _strict_legacy_record(root, component_name=comp_name, kind="provider")
                elif cts is not None:
                    _strict_legacy_record(root, component_name=comp_name, kind="class_consumer")
            # Persist class instance on fiber.state_node.
            if fiber.alternate is not None and fiber.alternate.state_node is not None:
                instance = fiber.alternate.state_node
            else:
                # DEV StrictMode: construct twice on mount (discarded instance first).
                if pre_dev_strict_dbl:
                    node.type(**dict(props_for_component_render(node.type, node.props)))
                instance = node.type(**dict(props_for_component_render(node.type, node.props)))
                fiber._is_new_instance = True  # type: ignore[attr-defined]
            assert isinstance(instance, Component)
            # Update props/stateful instance for this render.
            prev_props = dict(getattr(instance, "_props", {}) or {})
            prev_state_obj = getattr(instance, "_state", {})
            prev_state = dict(prev_state_obj) if isinstance(prev_state_obj, dict) else {}
            next_props = dict(node.props)
            instance._props = next_props  # type: ignore[attr-defined]
            if isinstance(ct, Context):
                instance._context = ct._get()  # type: ignore[attr-defined]
            else:
                instance._context = None  # type: ignore[attr-defined]
            raw_state = getattr(instance, "_state", None)
            if is_dev() and raw_state is not None and not isinstance(raw_state, dict):
                stack = component_stack_from_fiber(fiber)
                msg = "The initial state must be a mapping (dict-like)."
                if stack:
                    msg = msg + "\n\n" + stack
                warnings.warn(msg, RuntimeWarning, stacklevel=2)
                try:
                    instance._state = {}  # type: ignore[attr-defined]
                except Exception:
                    pass
            elif raw_state is None:
                # Upstream: class state may be null; treat it as an empty mapping.
                if is_dev():
                    gdsfp_raw = getattr(type(instance), "getDerivedStateFromProps", None)
                    if callable(gdsfp_raw):
                        stack = component_stack_from_fiber(fiber)
                        msg = (
                            "State must be initialized before "
                            "static getDerivedStateFromProps() is called."
                        )
                        if stack:
                            msg = msg + "\n\n" + stack
                        warnings.warn(msg, RuntimeWarning, stacklevel=2)
                try:
                    instance._state = {}  # type: ignore[attr-defined]
                except Exception:
                    pass
            if is_dev():
                raw = getattr(type(instance), "__dict__", {}).get("getSnapshotBeforeUpdate")
                if isinstance(raw, staticmethod):
                    stack = component_stack_from_fiber(fiber)
                    msg = "getSnapshotBeforeUpdate() must not be declared as a staticmethod."
                    if stack:
                        msg = msg + "\n\n" + stack
                    warnings.warn(msg, RuntimeWarning, stacklevel=2)
                # Common misspellings warned by React.
                # (Keep this minimal; expand only as tests demand.)
                misspellings = [
                    ("componentWillReceiveProps", "componentWillRecieveProps"),
                    ("shouldComponentUpdate", "shouldComponentUpdatee"),
                    ("UNSAFE_componentWillReceiveProps", "UNSAFE_componentWillRecieveProps"),
                ]
                for expected, bad in misspellings:
                    if hasattr(type(instance), bad) and not hasattr(type(instance), expected):
                        stack = component_stack_from_fiber(fiber)
                        msg = f"Did you mean `{expected}`? Found `{bad}`."
                        if stack:
                            msg = msg + "\n\n" + stack
                        warnings.warn(msg, RuntimeWarning, stacklevel=2)
            # Attach class component refs early so lifecycles observe them.
            if node.ref is not None:
                try:
                    if callable(node.ref):
                        node.ref(instance)
                    elif hasattr(node.ref, "current"):
                        node.ref.current = instance
                except Exception:
                    # Upstream: ref failures should not abort render.
                    pass
            # Provide a renderer-owned schedule hook for setState.
            from .concurrent import current_update_lane

            def _schedule_for_setstate() -> None:
                forced_sync = bool(getattr(root, "_force_sync_updates", False))
                batched = bool(getattr(root, "_is_batching_updates", False))
                lane_override = current_update_lane()
                if lane_override is not None:
                    schedule_update(lane_override)
                    return
                # If we're in commit lifecycles (cDM/cDU), updates are Task/sync unless
                # explicitly wrapped in start_transition.
                if _current_commit_phase is not None:
                    if forced_sync or not batched:
                        schedule_update(SYNC_LANE)
                    else:
                        schedule_update(DEFAULT_LANE)
                    return
                schedule_update(root._current_lane)

            instance._schedule_update = _schedule_for_setstate  # type: ignore[attr-defined]
            fiber.state_node = instance
            # Legacy unsafe lifecycles run during render (pre-commit).
            if fiber.alternate is None:
                cwm = getattr(instance, "UNSAFE_componentWillMount", None)
                if callable(cwm):
                    cwm()
                # Apply queued state updates before the first render, including
                # updates enqueued during UNSAFE_componentWillMount.
                pending = getattr(instance, "_pending_state_updates", None)
                if isinstance(pending, list) and pending:
                    visible_pri = root._current_lane.priority
                    remaining: list[tuple[Lane, Any]] = []
                    for item in pending:
                        if not (
                            isinstance(item, tuple)
                            and len(item) in (2, 3)
                            and isinstance(item[0], Lane)
                        ):
                            continue
                        lane = item[0]
                        patch = item[1]
                        replace = bool(item[2]) if len(item) == 3 else False
                        if lane.priority <= visible_pri:
                            if callable(patch):
                                # DEV StrictMode: updater functions are invoked twice.
                                next_patch = patch(instance.state, instance.props)
                                if strict and is_dev():
                                    try:
                                        _ = patch(instance.state, instance.props)
                                    except Exception:
                                        pass
                                if isinstance(next_patch, dict):
                                    if replace:
                                        instance._state = dict(next_patch)  # type: ignore[attr-defined]
                                    else:
                                        instance._state.update(next_patch)  # type: ignore[attr-defined]
                            elif isinstance(patch, dict):
                                if replace:
                                    instance._state = dict(patch)  # type: ignore[attr-defined]
                                else:
                                    instance._state.update(patch)  # type: ignore[attr-defined]
                        else:
                            remaining.append((lane, patch, replace))
                    pending[:] = remaining
                # New lifecycle: static getDerivedStateFromProps runs before the
                # initial render.
                gdsfp = getattr(type(instance), "getDerivedStateFromProps", None)
                if is_dev():
                    raw = getattr(type(instance), "__dict__", {}).get("getDerivedStateFromProps")
                    if raw is not None and not isinstance(raw, staticmethod) and callable(raw):
                        stack = component_stack_from_fiber(fiber)
                        msg = "getDerivedStateFromProps() must be declared as a staticmethod."
                        if stack:
                            msg = msg + "\n\n" + stack
                        warnings.warn(msg, RuntimeWarning, stacklevel=2)
                        # Avoid calling an instance method as a static lifecycle.
                        gdsfp = None
                    if callable(gdsfp) and not isinstance(getattr(instance, "_state", None), dict):
                        stack = component_stack_from_fiber(fiber)
                        msg = "State must be initialized before static getDerivedStateFromProps."
                        if stack:
                            msg = msg + "\n\n" + stack
                        warnings.warn(msg, RuntimeWarning, stacklevel=2)
                if callable(gdsfp):
                    ps = dict(instance.props)
                    st = dict(instance.state)
                    next_state = gdsfp(ps, st)
                    if pre_dev_strict_dbl:
                        _ = gdsfp(ps, st)
                    if isinstance(next_state, dict):
                        instance._state.update(dict(next_state))  # type: ignore[attr-defined]
            else:
                # Apply queued state updates before render.
                pending = getattr(instance, "_pending_state_updates", None)
                if isinstance(pending, list) and pending:
                    visible_pri = root._current_lane.priority
                    # React processes updates sequentially; for our early model, each
                    # scheduled root update corresponds to a single render. To preserve
                    # insertion order semantics (and make intermediate states observable),
                    # apply at most one eligible patch per render.
                    applied = False
                    remaining: list[tuple[Lane, Any]] = []
                    for item in pending:
                        if not (
                            isinstance(item, tuple)
                            and len(item) in (2, 3)
                            and isinstance(item[0], Lane)
                        ):
                            continue
                        lane = item[0]
                        patch = item[1]
                        replace = bool(item[2]) if len(item) == 3 else False
                        if not applied and lane.priority <= visible_pri:
                            if callable(patch):
                                next_patch = patch(prev_state, prev_props)
                                if strict and is_dev():
                                    try:
                                        _ = patch(prev_state, prev_props)
                                    except Exception:
                                        pass
                                if isinstance(next_patch, dict):
                                    if replace:
                                        instance._state = dict(next_patch)  # type: ignore[attr-defined]
                                    else:
                                        instance._state.update(next_patch)  # type: ignore[attr-defined]
                            elif isinstance(patch, dict):
                                if replace:
                                    instance._state = dict(patch)  # type: ignore[attr-defined]
                                else:
                                    instance._state.update(patch)  # type: ignore[attr-defined]
                            applied = True
                        else:
                            remaining.append((lane, patch, replace))
                    pending[:] = remaining
                # New lifecycle: static getDerivedStateFromProps runs before each
                # update render.
                gdsfp = getattr(type(instance), "getDerivedStateFromProps", None)
                if is_dev():
                    raw = getattr(type(instance), "__dict__", {}).get("getDerivedStateFromProps")
                    if raw is not None and not isinstance(raw, staticmethod) and callable(raw):
                        stack = component_stack_from_fiber(fiber)
                        msg = "getDerivedStateFromProps() must be declared as a staticmethod."
                        if stack:
                            msg = msg + "\n\n" + stack
                        warnings.warn(msg, RuntimeWarning, stacklevel=2)
                        gdsfp = None
                    if callable(gdsfp) and not isinstance(getattr(instance, "_state", None), dict):
                        stack = component_stack_from_fiber(fiber)
                        msg = "State must be initialized before static getDerivedStateFromProps."
                        if stack:
                            msg = msg + "\n\n" + stack
                        warnings.warn(msg, RuntimeWarning, stacklevel=2)
                if callable(gdsfp):
                    ps2 = dict(instance.props)
                    st2 = dict(instance.state) if isinstance(getattr(instance, "_state", None), dict) else {}
                    next_state = gdsfp(ps2, st2)
                    if pre_dev_strict_dbl:
                        _ = gdsfp(ps2, st2)
                    if isinstance(next_state, dict):
                        instance._state.update(dict(next_state))  # type: ignore[attr-defined]
                cwu = getattr(instance, "UNSAFE_componentWillUpdate", None)
                if callable(cwu) and not reappearing:
                    cwu()
            # Flush pending setState callbacks after commit (when visible).
            if visible:
                callbacks = list(getattr(instance, "_pending_setstate_callbacks", []))
                getattr(instance, "_pending_setstate_callbacks", []).clear()
                for cb2 in callbacks:
                    if strict and is_dev():
                        # DEV StrictMode: setState callbacks are invoked twice.
                        def _call_cb2(fn: Any = cb2) -> None:
                            fn()

                        commit_callbacks_fc.append(_call_cb2)

                    def _call_cb(fn: Any = cb2) -> None:
                        fn()

                    commit_callbacks_fc.append(_call_cb)

            did_bail_out = False
            if fiber.alternate is not None and not reappearing:
                forced = bool(getattr(instance, "_force_update", False))  # type: ignore[attr-defined]
                if forced:
                    try:
                        instance._force_update = False  # type: ignore[attr-defined]
                    except Exception:
                        pass
                scu = getattr(instance, "shouldComponentUpdate", None)
                if callable(scu) and not forced:
                    if is_dev():
                        try:
                            from .component import PureComponent

                            if isinstance(instance, PureComponent):
                                raw = getattr(type(instance), "__dict__", {}).get(
                                    "shouldComponentUpdate"
                                )
                                if raw is not None:
                                    stack = component_stack_from_fiber(fiber)
                                    msg = (
                                        "shouldComponentUpdate should not be defined on "
                                        "PureComponent; consider extending Component instead."
                                    )
                                    if stack:
                                        msg = msg + "\n\n" + stack
                                    warnings.warn(msg, RuntimeWarning, stacklevel=2)
                        except Exception:
                            pass
                    try:
                        next_state_obj = getattr(instance, "_state", {})
                        next_state = (
                            dict(next_state_obj) if isinstance(next_state_obj, dict) else {}
                        )
                        # React calls SCU with next props/state while `this.props/state`
                        # still refer to the previous values.
                        instance._props = prev_props  # type: ignore[attr-defined]
                        instance._state = prev_state  # type: ignore[attr-defined]
                        should_update = bool(scu(next_props, next_state))  # type: ignore[misc]
                        if pre_dev_strict_dbl:
                            _ = scu(next_props, next_state)  # type: ignore[misc]
                    except Exception as err:
                        if "Component stack:" not in str(err):
                            stack = component_stack_from_fiber(fiber)
                            if stack:
                                err.args = (f"{err}\n\n{stack}",) + tuple(err.args[1:])
                        raise
                    finally:
                        instance._props = next_props  # type: ignore[attr-defined]
                        instance._state = next_state  # type: ignore[attr-defined]
                    if not should_update:
                        rendered_comp = getattr(instance, "_ryact_last_rendered", None)  # type: ignore[attr-defined]
                        did_bail_out = rendered_comp is not None

            if not did_bail_out:
                # Class `render` must not run inside the hook frame: hooks are only
                # valid in function components (unlike a mistaken hook call inside
                # `render` when wrapped, which would incorrectly succeed).
                try:
                    from .element import _with_current_owner

                    with (
                        _with_update_lane(root._current_lane),
                        _with_current_owner(type(instance).__name__),
                    ):
                        from .context import _with_current_context_consumer

                        with _with_current_context_consumer(fiber):
                            if pre_dev_strict_dbl and fiber.alternate is None:
                                prev_discard = _strict_discard_class_render[0]
                                _strict_discard_class_render[0] = True
                                try:
                                    _ = instance.render()
                                finally:
                                    _strict_discard_class_render[0] = prev_discard
                            rendered_comp = instance.render()
                except Exception as err:
                    if "Component stack:" not in str(err):
                        stack = component_stack_from_fiber(fiber)
                        if stack:
                            err.args = (f"{err}\n\n{stack}",) + tuple(err.args[1:])
                    raise
                try:
                    instance._ryact_last_rendered = rendered_comp  # type: ignore[attr-defined]
                except Exception:
                    # Some user components declare restrictive __slots__.
                    pass
        else:
            from .concurrent import _with_update_lane
            from .dev import is_dev

            ct = getattr(node.type, "contextType", None)
            if is_dev() and ct is not None:
                stack = component_stack_from_fiber(fiber)
                msg = "contextType cannot be defined on a function component."
                if stack:
                    msg = msg + "\n\n" + stack
                warnings.warn(msg, RuntimeWarning, stacklevel=2)
            if pre_dev_strict_dbl and getattr(node.type, "contextTypes", None) is not None:
                _strict_legacy_record(
                    root,
                    component_name=getattr(node.type, "__name__", "Unknown"),
                    kind="fn_consumer",
                )

            try:
                if strict and fiber.alternate is None:
                    with _with_update_lane(root._current_lane):
                        from .element import _with_current_owner

                        with _with_current_owner(getattr(node.type, "__name__", None)):
                            _ = _render_with_hooks(
                                node.type,
                                dict(props_for_component_render(node.type, node.props)),
                                fiber.hooks,
                                scheduled_insertion_effects=insertion_effects_fc,
                                scheduled_layout_effects=layout_effects_fc,
                                scheduled_passive_effects=passive_effects_fc,
                                scheduled_strict_layout_effects=strict_layout_effects_fc,
                                scheduled_strict_passive_effects=strict_passive_effects_fc,
                                schedule_update=schedule_update,
                                default_lane=root._current_lane,
                                next_id=next_id,
                                visible=visible,
                                strict_effects=strict,
                                reappearing=reappearing,
                            )
                            insertion_effects_fc.clear()
                            layout_effects_fc.clear()
                            passive_effects_fc.clear()
                            strict_layout_effects_fc.clear()
                            strict_passive_effects_fc.clear()
                with _with_update_lane(root._current_lane):
                    from .element import _with_current_owner

                    with _with_current_owner(getattr(node.type, "__name__", None)):
                        from .context import _with_current_context_consumer

                        with _with_current_context_consumer(fiber):
                            rendered_comp = _render_with_hooks(
                                node.type,
                                dict(props_for_component_render(node.type, node.props)),
                                fiber.hooks,
                                scheduled_insertion_effects=insertion_effects_fc,
                                scheduled_layout_effects=layout_effects_fc,
                                scheduled_passive_effects=passive_effects_fc,
                                scheduled_strict_layout_effects=strict_layout_effects_fc,
                                scheduled_strict_passive_effects=strict_passive_effects_fc,
                                schedule_update=schedule_update,
                                default_lane=root._current_lane,
                                next_id=next_id,
                                visible=visible,
                                strict_effects=strict,
                                reappearing=reappearing,
                                strict_remaining_mount_pass=bool(strict and fiber.alternate is None),
                            )
            except Exception as err:
                if "Component stack:" not in str(err):
                    stack = component_stack_from_fiber(fiber)
                    if stack:
                        err.args = (f"{err}\n\n{stack}",) + tuple(err.args[1:])
                raise

        # Wrap effect runners so hook setters can detect commit phase + attach stacks.
        stack_str = component_stack_from_fiber(fiber)
        wrapped_insertion: list[Callable[[], None]] = []
        for run in insertion_effects_fc:

            def _wrap_insertion(fn: Callable[[], None] = run, st: str = stack_str) -> None:
                _set_commit_context(phase="insertion", stack=st or None)
                try:
                    fn()
                finally:
                    _set_commit_context(phase=None, stack=None)

            wrapped_insertion.append(_wrap_insertion)
        insertion_effects_fc = wrapped_insertion

        rendered_comp = coerce_top_level_render_result(rendered_comp)
        try:
            child_work = _render_noop(
                rendered_comp,
                root,
                _child_identity_path(identity_path, 0, rendered_comp),
                next_id,
                parent_fiber=fiber,
                index=0,
                strict=strict,
                visible=visible,
                reappearing=reappearing,
            )
        except BaseException as err:
            # Best-effort: attach a deterministic component stack to raised errors.
            # Error boundary handling below may recover; only annotate if re-raising.
            if isinstance(err, Exception) and "Component stack:" not in str(err):
                stack = component_stack_from_fiber(fiber)
                if stack:
                    err.args = (f"{err}\n\n{stack}",) + tuple(err.args[1:])
            inst = fiber.state_node
            is_boundary = inst is not None and (
                callable(getattr(inst, "componentDidCatch", None))
                or callable(getattr(type(inst), "getDerivedStateFromError", None))
            )
            if not is_boundary:
                raise

            # Apply derived state and schedule didCatch for commit.
            gdsfe = getattr(type(inst), "getDerivedStateFromError", None)
            did_catch = getattr(inst, "componentDidCatch", None)
            from .dev import is_dev
            if is_dev():
                raw = getattr(type(inst), "__dict__", {}).get("getDerivedStateFromError")
                if raw is not None and not isinstance(raw, staticmethod) and callable(raw):
                    stack = component_stack_from_fiber(fiber)
                    msg = "getDerivedStateFromError() must be declared as a staticmethod."
                    if stack:
                        msg = msg + "\n\n" + stack
                    warnings.warn(msg, RuntimeWarning, stacklevel=2)
                    gdsfe = None

            def _log_captured_error(e: BaseException) -> None:
                reporter = getattr(root.container_info, "captured_error_reporter", None)
                if not callable(reporter):
                    return
                # Prevent cycles if logging throws while already logging.
                if bool(getattr(root, "_is_reporting_error", False)):
                    return
                root._is_reporting_error = True  # type: ignore[attr-defined]
                try:
                    try:
                        reporter(e)
                    except BaseException as log_err:
                        # If error reporting itself fails, do not attempt any root-level retries.
                        with suppress(Exception):
                            log_err._ryact_no_root_retry = True  # type: ignore[attr-defined]
                        raise
                finally:
                    root._is_reporting_error = False  # type: ignore[attr-defined]

            # Legacy boundaries without GDSFE: the initial render+child may throw once; we then
            # retry a single (render, _render_noop) pair before running componentDidCatch, matching
            # the upstream "retry once" model (two child failures before handling).
            if not callable(gdsfe) and callable(did_catch):
                try:
                    retried = inst.render()
                    child_work = _render_noop(
                        retried,
                        root,
                        identity_path,
                        next_id,
                        parent_fiber=fiber,
                        index=0,
                        strict=strict,
                        visible=visible,
                        reappearing=reappearing,
                    )
                except BaseException as err_retry:
                    # Second child failure: handle and render fallback.
                    _log_captured_error(err_retry)
                    try:
                        did_catch(err_retry)
                    except BaseException as re:
                        try:
                            re._ryact_boundary_rethrow = True  # type: ignore[attr-defined]
                        except Exception:
                            pass
                        raise
                    if fiber.alternate is None:
                        fiber._did_catch_during_mount = True  # type: ignore[attr-defined]
                    _apply_queued_class_state_for_sync_render(
                        inst, root, strict=strict
                    )
                    recovered = inst.render()
                    child_work = _render_noop(
                        recovered,
                        root,
                        identity_path,
                        next_id,
                        parent_fiber=fiber,
                        index=0,
                        strict=strict,
                        visible=visible,
                        reappearing=reappearing,
                    )
                # didCatch executed synchronously above; do not schedule a commit callback.
                fiber.child = child_work.finished_work
                if visible:
                    layout_effects_fc.extend(child_work.layout_effects)
                    passive_effects_fc.extend(child_work.passive_effects)
                    strict_layout_effects_fc.extend(child_work.strict_layout_effects)
                    strict_passive_effects_fc.extend(child_work.strict_passive_effects)
                    commit_callbacks_fc.extend(child_work.commit_callbacks)
                    # Class boundary lifecycles for this handled-error path.
                    did_catch_during_mount = getattr(fiber, "_did_catch_during_mount", False)
                    if _is_class_component(node.type) and did_catch_during_mount:

                            def _did_update_after_catch(inst2: Any = inst) -> None:
                                cb = getattr(inst2, "componentDidUpdate", None)
                                if callable(cb):
                                    cb()

                            commit_callbacks_fc.append(_did_update_after_catch)
                fiber.memoized_props = dict(node.props)
                fiber.memoized_snapshot = child_work.snapshot
                return NoopWork(
                    snapshot=child_work.snapshot,
                    insertion_effects=insertion_effects_fc if visible else [],
                    layout_effects=layout_effects_fc if visible else [],
                    passive_effects=passive_effects_fc if visible else [],
                    strict_layout_effects=strict_layout_effects_fc if visible else [],
                    strict_passive_effects=strict_passive_effects_fc if visible else [],
                    commit_callbacks=commit_callbacks_fc if visible else [],
                    finished_work=fiber,
                )
            if callable(gdsfe):
                _log_captured_error(err)
                partial = gdsfe(err)
                if isinstance(partial, dict):
                    inst._state.update(partial)  # type: ignore[attr-defined]

            # Re-render boundary with updated state to produce fallback output.
            recovered = inst.render()
            try:
                child_work = _render_noop(
                    recovered,
                    root,
                    identity_path,
                    next_id,
                    parent_fiber=fiber,
                    index=0,
                    strict=strict,
                    visible=visible,
                    reappearing=reappearing,
                )
            except BaseException as err_inner:
                # Recovery render failed (e.g. noop boundary rethrows from render). React invokes
                # ``componentDidCatch`` before surfacing the error; there is no successful commit.
                if callable(did_catch):
                    did_catch(err_inner)
                raise
            else:
                if callable(did_catch):

                    def _call_did_catch(fn: Any = did_catch, e: BaseException = err) -> None:
                        fn(e)

                    commit_callbacks_fc.append(_call_did_catch)

        fiber.child = child_work.finished_work
        if visible:
            class_did_mount_for_layout: list[Callable[[], None]] = []

            # Class component lifecycles: mount/update ordering vs descendant layout effects.
            inst2 = fiber.state_node if _is_class_component(node.type) else None
            if inst2 is not None:
                if fiber.alternate is not None and fiber.alternate.state_node is not None:
                    if not reappearing:

                        def _did_update(inst: Any = inst2) -> None:
                            cb = getattr(inst, "componentDidUpdate", None)
                            if callable(cb):
                                cb()

                        commit_callbacks_fc.append(_did_update)
                elif getattr(fiber, "_is_new_instance", False):
                    if getattr(fiber, "_did_catch_during_mount", False):

                        def _did_update_after_catch(inst: Any = inst2) -> None:
                            cb = getattr(inst, "componentDidUpdate", None)
                            if callable(cb):
                                cb()

                        commit_callbacks_fc.append(_did_update_after_catch)
                    else:

                        def _did_mount(inst: Any = inst2) -> None:
                            cb = getattr(inst, "componentDidMount", None)
                            if callable(cb):
                                cb()

                        class_did_mount_for_layout.append(_did_mount)
                    from .dev import is_dev

                    if strict and is_dev():

                        def _strict_class_will_unmount(inst: Any = inst2) -> None:
                            w = getattr(inst, "componentWillUnmount", None)
                            if callable(w):
                                w()

                        def _strict_class_did_mount(inst: Any = inst2) -> None:
                            m = getattr(inst, "componentDidMount", None)
                            if callable(m):
                                m()

                        wu_tagged = _tag_effect(_strict_class_will_unmount, phase="destroy")
                        with suppress(Exception):
                            wu_tagged._ryact_strict_class_unmount = True  # type: ignore[attr-defined]
                        strict_layout_effects_fc.append(wu_tagged)
                        strict_layout_effects_fc.append(
                            _tag_effect(_strict_class_did_mount, phase="create")
                        )

            layout_effects_fc.extend(class_did_mount_for_layout)
            layout_effects_fc.extend(child_work.layout_effects)
            passive_effects_fc.extend(child_work.passive_effects)
            strict_layout_effects_fc.extend(child_work.strict_layout_effects)
            strict_passive_effects_fc.extend(child_work.strict_passive_effects)
            commit_callbacks_fc.extend(child_work.commit_callbacks)
        fiber.memoized_props = dict(node.props)
        fiber.memoized_snapshot = child_work.snapshot
        return NoopWork(
            snapshot=child_work.snapshot,
            insertion_effects=insertion_effects_fc if visible else [],
            layout_effects=layout_effects_fc if visible else [],
            passive_effects=passive_effects_fc if visible else [],
            strict_layout_effects=strict_layout_effects_fc if visible else [],
            strict_passive_effects=strict_passive_effects_fc if visible else [],
            commit_callbacks=commit_callbacks_fc if visible else [],
            finished_work=fiber,
        )

    # Upstream: invalid element types should produce a helpful error message that
    # includes component stack context.
    #
    # Note: at this point we may not have created a Fiber for `node` yet, so use the
    # parent fiber for stack context (it still points at the owner chain).
    stack = component_stack_from_fiber(parent_fiber)
    if node.type is None:
        got = "null"
    elif isinstance(node.type, bool):
        got = "boolean"
    elif isinstance(node.type, (int, float)):
        got = "number"
    else:
        got = type(node.type).__name__
    msg = (
        "Element type is invalid: expected a string (for built-in components) "
        f"or a class/function (for composite components) but got: {got}."
    )
    if stack:
        msg = msg + "\n\n" + stack
    raise TypeError(msg)


def render_to_noop_work(root: Root, element: Element | None) -> NoopWork:
    """Render phase for noop host: compute snapshot + effect lists."""
    counter = 0

    def next_id() -> str:
        nonlocal counter
        counter += 1
        return f"rid-{counter}"

    if root.current is None:
        root.current = Fiber(type="__root__", key=None, pending_props={})
    wip_root = Fiber(type="__root__", key=None, pending_props={}, alternate=root.current)
    with suppress(Exception):
        root._strict_legacy_pending = []  # type: ignore[attr-defined]
    work = _render_noop(element, root, "0", next_id, parent_fiber=wip_root, index=0)
    wip_root.child = work.finished_work
    commit_callbacks = list(work.commit_callbacks)
    commit_callbacks.extend(_strict_lifecycle_flush(root))
    commit_callbacks.extend(_strict_legacy_flush(root))
    return NoopWork(
        snapshot=work.snapshot,
        insertion_effects=work.insertion_effects,
        layout_effects=work.layout_effects,
        passive_effects=work.passive_effects,
        strict_layout_effects=work.strict_layout_effects,
        strict_passive_effects=work.strict_passive_effects,
        commit_callbacks=commit_callbacks,
        finished_work=wip_root,
    )


def render_to_noop_snapshot(root: Root, element: Element | None) -> Any:
    """Compatibility helper: render a noop snapshot only (no effect execution)."""
    return render_to_noop_work(root, element).snapshot
