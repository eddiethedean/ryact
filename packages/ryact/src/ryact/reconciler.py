from __future__ import annotations

import warnings
from collections.abc import Callable
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
from .element import Element, create_element
from .hooks import (
    _current_commit_phase,
    _is_class_component,
    _render_with_hooks,
    _set_commit_context,
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
    alt = alt_children[index] if index < len(alt_children) else None
    if alt is not None and alt.key == key and alt.type == type_:
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
    updates.sort(key=lambda u: u.lane.priority)
    for u in updates:
        root._current_lane = u.lane
        if isinstance(u.payload, Element) or u.payload is None:
            root._last_element = u.payload
        render(u.payload)


Renderable = Element | str | int | float | None


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

    # Host element: string tag
    if isinstance(node.type, str):
        fiber = _reconcile_child(
            parent_fiber,
            index=index,
            type_=node.type,
            key=node.key,
            pending_props={**dict(node.props), "__ref__": node.ref},
        )
        if node.type == "__offscreen__":
            # Minimal Offscreen/Activity-like wrapper for noop host.
            mode = None
            if isinstance(node.props, dict):
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
            children = node.props.get("children", ()) if isinstance(node.props, dict) else ()
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
        if node.type in ("__js_subtree__", "__py_subtree__"):
            runner = getattr(root.container_info, "interop_runner", None)
            if runner is None:
                raise RuntimeError(
                    "Interop boundary encountered but no interop_runner is configured "
                    "on the noop root."
                )
            boundary_id = identity_path
            props = node.props.get("props") if isinstance(node.props, dict) else None
            children = node.props.get("children", ()) if isinstance(node.props, dict) else ()
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
                    f"{identity_path}.{i}",
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
        if node.type == "__strict_mode__":
            from .dev import is_dev

            children = node.props.get("children", ())
            child = children[0] if children else None
            work = _render_noop(
                child,
                root,
                f"{identity_path}.sm",
                next_id,
                parent_fiber=fiber,
                index=0,
                strict=strict or is_dev(),
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
                    f"{identity_path}.s",
                    next_id,
                    parent_fiber=fiber,
                    index=0,
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
                f"{identity_path}.{i}",
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
        prev_props = dict(fiber.alternate.memoized_props) if fiber.alternate is not None else None
        next_props = dict(node.props)
        compare = node.type.compare
        equal = False
        if prev_props is not None:
            if compare is not None:
                equal = bool(compare(prev_props, next_props))
            else:
                equal = shallow_equal_props(prev_props, next_props)

        if equal and fiber.alternate is not None:
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
        if isinstance(node.ref, str):
            raise TypeError("String refs are not supported on ref-receiving components.")
        rendered = node.type.render(dict(node.props), node.ref)
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
        insertion_effects_fc: list[Callable[[], None]] = []
        layout_effects_fc: list[Callable[[], None]] = []
        passive_effects_fc: list[Callable[[], None]] = []
        strict_layout_effects_fc: list[Callable[[], None]] = []
        strict_passive_effects_fc: list[Callable[[], None]] = []
        commit_callbacks_fc: list[Callable[[], None]] = []

        def schedule_update(lane: Lane) -> None:
            schedule_update_on_root(root, Update(lane=lane, payload=root._last_element))

        rendered_comp: Any
        if _is_class_component(node.type):
            from .dev import is_dev
            from .concurrent import _with_update_lane

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
            # Persist class instance on fiber.state_node.
            if fiber.alternate is not None and fiber.alternate.state_node is not None:
                instance = fiber.alternate.state_node
            else:
                instance = node.type(**dict(node.props))
                fiber._is_new_instance = True  # type: ignore[attr-defined]
            assert isinstance(instance, Component)
            # Update props/stateful instance for this render.
            instance._props = dict(node.props)  # type: ignore[attr-defined]
            if is_dev() and not isinstance(getattr(instance, "_state", None), dict):
                stack = component_stack_from_fiber(fiber)
                msg = "The initial state must be a mapping (dict-like)."
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
                                next_patch = patch(instance.state, instance.props)
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
                    next_state = gdsfp(instance.props, instance.state)
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
                                next_patch = patch(instance.state, instance.props)
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
                    next_state = gdsfp(instance.props, instance.state)
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
                    try:
                        should_update = bool(scu(instance._props, instance._state))  # type: ignore[attr-defined]
                    except Exception as err:
                        if "Component stack:" not in str(err):
                            stack = component_stack_from_fiber(fiber)
                            if stack:
                                err.args = (f"{err}\n\n{stack}",) + tuple(err.args[1:])
                        raise
                    if not should_update:
                        rendered_comp = getattr(instance, "_ryact_last_rendered", None)  # type: ignore[attr-defined]
                        did_bail_out = rendered_comp is not None

            def _call_render(**_: Any) -> Any:
                return instance.render()

            if not did_bail_out:
                try:
                    with _with_update_lane(root._current_lane):
                        rendered_comp = _render_with_hooks(
                            _call_render,
                            {},
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

            try:
                if strict and fiber.alternate is None:
                    with _with_update_lane(root._current_lane):
                        _ = _render_with_hooks(
                            node.type,
                            dict(node.props),
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
                with _with_update_lane(root._current_lane):
                    rendered_comp = _render_with_hooks(
                        node.type,
                        dict(node.props),
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

        try:
            child_work = _render_noop(
                rendered_comp,
                root,
                identity_path,
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

            # Legacy boundaries without GDSFE: React retries once before handling.
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
                    # Second failure: handle and render fallback.
                    _log_captured_error(err_retry)
                    did_catch(err_retry)
                    if fiber.alternate is None:
                        fiber._did_catch_during_mount = True  # type: ignore[attr-defined]
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
            layout_effects_fc.extend(child_work.layout_effects)
            passive_effects_fc.extend(child_work.passive_effects)
            strict_layout_effects_fc.extend(child_work.strict_layout_effects)
            strict_passive_effects_fc.extend(child_work.strict_passive_effects)
            commit_callbacks_fc.extend(child_work.commit_callbacks)

        # Class component lifecycles: decide mount vs update after child render/error handling.
        if _is_class_component(node.type):
            inst2 = fiber.state_node
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

                        commit_callbacks_fc.append(_did_mount)
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

    raise TypeError(f"Unsupported element type: {node.type!r}")


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
    work = _render_noop(element, root, "0", next_id, parent_fiber=wip_root, index=0)
    wip_root.child = work.finished_work
    return NoopWork(
        snapshot=work.snapshot,
        insertion_effects=work.insertion_effects,
        layout_effects=work.layout_effects,
        passive_effects=work.passive_effects,
        strict_layout_effects=work.strict_layout_effects,
        strict_passive_effects=work.strict_passive_effects,
        commit_callbacks=work.commit_callbacks,
        finished_work=wip_root,
    )


def render_to_noop_snapshot(root: Root, element: Element | None) -> Any:
    """Compatibility helper: render a noop snapshot only (no effect execution)."""
    return render_to_noop_work(root, element).snapshot
