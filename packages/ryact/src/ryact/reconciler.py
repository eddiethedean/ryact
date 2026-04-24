from __future__ import annotations

import warnings
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Optional

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
from .element import Element
from .hooks import _is_class_component, _render_with_hooks


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
            commit_callbacks=[],
            finished_work=None,
        )
    if isinstance(node, (str, int, float)):
        return NoopWork(
            snapshot=str(node),
            insertion_effects=[],
            layout_effects=[],
            passive_effects=[],
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
        if node.type == "__fragment__":
            children = node.props.get("children", ())
            rendered_children: list[Any] = []
            insertion_effects: list[Callable[[], None]] = []
            layout_effects: list[Callable[[], None]] = []
            passive_effects: list[Callable[[], None]] = []
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
                )
                if isinstance(w.snapshot, list):
                    rendered_children.extend(w.snapshot)
                else:
                    rendered_children.append(w.snapshot)
                insertion_effects.extend(w.insertion_effects)
                layout_effects.extend(w.layout_effects)
                passive_effects.extend(w.passive_effects)
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
            )
            fiber.child = work.finished_work
            return NoopWork(
                snapshot=work.snapshot,
                insertion_effects=work.insertion_effects,
                layout_effects=work.layout_effects,
                passive_effects=work.passive_effects,
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
                    child, root, f"{identity_path}.s", next_id, parent_fiber=fiber, index=0
                )
                fiber.child = work.finished_work
                return NoopWork(
                    snapshot=work.snapshot,
                    insertion_effects=work.insertion_effects,
                    layout_effects=work.layout_effects,
                    passive_effects=work.passive_effects,
                    commit_callbacks=work.commit_callbacks,
                    finished_work=fiber,
                )
            except Suspend as s:

                def wake() -> None:
                    if root._last_element is None:
                        return
                    schedule_update_on_root(
                        root, Update(lane=DEFAULT_LANE, payload=root._last_element)
                    )

                s.thenable.then(wake)
                work = _render_noop(
                    fallback, root, f"{identity_path}.f", next_id, parent_fiber=fiber, index=0
                )
                fiber.child = work.finished_work
                return NoopWork(
                    snapshot=work.snapshot,
                    insertion_effects=work.insertion_effects,
                    layout_effects=work.layout_effects,
                    passive_effects=work.passive_effects,
                    commit_callbacks=work.commit_callbacks,
                    finished_work=fiber,
                )

        children = node.props.get("children", ())
        rendered_children: list[Any] = []
        insertion_effects: list[Callable[[], None]] = []
        layout_effects: list[Callable[[], None]] = []
        passive_effects: list[Callable[[], None]] = []
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
            )
            if isinstance(w.snapshot, list):
                rendered_children.extend(w.snapshot)
            else:
                rendered_children.append(w.snapshot)
            insertion_effects.extend(w.insertion_effects)
            layout_effects.extend(w.layout_effects)
            passive_effects.extend(w.passive_effects)
            commit_callbacks.extend(w.commit_callbacks)
            if w.finished_work is not None:
                if prev_child is None:
                    fiber.child = w.finished_work
                else:
                    prev_child.sibling = w.finished_work
                prev_child = w.finished_work

        snap = {
            "type": node.type,
            "key": node.key,
            "props": {k: v for k, v in dict(node.props).items() if k != "children"},
            "children": rendered_children,
        }
        return NoopWork(
            snapshot=snap,
            insertion_effects=insertion_effects,
            layout_effects=layout_effects,
            passive_effects=passive_effects,
            commit_callbacks=commit_callbacks,
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
        insertion_effects: list[Callable[[], None]] = []
        layout_effects: list[Callable[[], None]] = []
        passive_effects: list[Callable[[], None]] = []
        commit_callbacks: list[Callable[[], None]] = []

        def schedule_update(lane: Lane) -> None:
            schedule_update_on_root(root, Update(lane=lane, payload=root._last_element))

        rendered: Any
        if _is_class_component(node.type):
            from .dev import is_dev

            ct = getattr(node.type, "contextType", None)
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
                commit_callbacks.append(
                    lambda inst=instance: getattr(inst, "componentDidMount", lambda: None)()
                )
            assert isinstance(instance, Component)
            # Update props/stateful instance for this render.
            instance._props = dict(node.props)  # type: ignore[attr-defined]
            fiber.state_node = instance
            if fiber.alternate is not None and fiber.alternate.state_node is not None:
                commit_callbacks.append(
                    lambda inst=instance: getattr(inst, "componentDidUpdate", lambda: None)()
                )

            def _call_render(**_: Any) -> Any:
                return instance.render()

            try:
                rendered = _render_with_hooks(
                    _call_render,
                    {},
                    fiber.hooks,
                    scheduled_insertion_effects=insertion_effects,
                    scheduled_layout_effects=layout_effects,
                    scheduled_passive_effects=passive_effects,
                    schedule_update=schedule_update,
                    default_lane=root._current_lane,
                    next_id=next_id,
                )
            except Exception as err:
                if "Component stack:" not in str(err):
                    stack = component_stack_from_fiber(fiber)
                    if stack:
                        err.args = (f"{err}\n\n{stack}",) + tuple(err.args[1:])
                raise
        else:
            try:
                if strict and fiber.alternate is None:
                    _ = _render_with_hooks(
                        node.type,
                        dict(node.props),
                        fiber.hooks,
                        scheduled_insertion_effects=insertion_effects,
                        scheduled_layout_effects=layout_effects,
                        scheduled_passive_effects=passive_effects,
                        schedule_update=schedule_update,
                        default_lane=root._current_lane,
                        next_id=next_id,
                    )
                rendered = _render_with_hooks(
                    node.type,
                    dict(node.props),
                    fiber.hooks,
                    scheduled_insertion_effects=insertion_effects,
                    scheduled_layout_effects=layout_effects,
                    scheduled_passive_effects=passive_effects,
                    schedule_update=schedule_update,
                    default_lane=root._current_lane,
                    next_id=next_id,
                )
            except Exception as err:
                if "Component stack:" not in str(err):
                    stack = component_stack_from_fiber(fiber)
                    if stack:
                        err.args = (f"{err}\n\n{stack}",) + tuple(err.args[1:])
                raise

        try:
            child_work = _render_noop(
                rendered, root, identity_path, next_id, parent_fiber=fiber, index=0, strict=strict
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
            if callable(gdsfe):
                partial = gdsfe(err)
                if isinstance(partial, dict):
                    inst._state.update(partial)  # type: ignore[attr-defined]
            did_catch = getattr(inst, "componentDidCatch", None)
            if callable(did_catch):
                commit_callbacks.append(lambda e=err, fn=did_catch: fn(e))

            # Re-render boundary with updated state to produce fallback output.
            recovered = inst.render()
            child_work = _render_noop(
                recovered,
                root,
                identity_path,
                next_id,
                parent_fiber=fiber,
                index=0,
                strict=strict,
            )

        fiber.child = child_work.finished_work
        layout_effects.extend(child_work.layout_effects)
        passive_effects.extend(child_work.passive_effects)
        commit_callbacks.extend(child_work.commit_callbacks)
        return NoopWork(
            snapshot=child_work.snapshot,
            insertion_effects=insertion_effects,
            layout_effects=layout_effects,
            passive_effects=passive_effects,
            commit_callbacks=commit_callbacks,
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
        commit_callbacks=work.commit_callbacks,
        finished_work=wip_root,
    )


def render_to_noop_snapshot(root: Root, element: Element | None) -> Any:
    """Compatibility helper: render a noop snapshot only (no effect execution)."""
    return render_to_noop_work(root, element).snapshot
