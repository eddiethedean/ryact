from __future__ import annotations

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

from .element import Element
from .hooks import _render_component


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


@dataclass
class Root:
    container_info: Any
    current: Fiber | None = None
    pending_updates: list[Update] = field(default_factory=list)
    scheduler: Optional[Scheduler] = None
    # Early “fiber-ish” identity model for hook slots without a full Fiber tree:
    # stable across re-renders as long as traversal order and keys are stable.
    _hooks_by_identity: dict[str, list[Any]] = field(default_factory=dict)
    _flush_task_id: int | None = None
    _flush_priority: int | None = None
    _commit_fn: Callable[[Any], Any] | None = None
    _current_element: Element | None = None
    _current_lane: Lane = field(default_factory=lambda: DEFAULT_LANE)
    _desired_element: Element | None = None


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
    root._desired_element = update.payload
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

    # Deterministic flush order by lane priority, then insertion order.
    updates = list(root.pending_updates)
    root.pending_updates.clear()
    updates.sort(key=lambda u: u.lane.priority)
    for u in updates:
        root._current_element = root._desired_element
        root._current_lane = u.lane
        render(root._current_element)


Renderable = Element | str | int | float | None


def _host_snapshot(node: Renderable, root: Root, identity_path: str) -> Any:
    """
    Deterministic snapshot renderer used by test harnesses (e.g. ryact-testkit’s noop renderer).

    This is intentionally minimal and exists to support Milestone 3 test translation work.
    DOM/native renderers remain separate.
    """
    if node is None:
        return None
    if isinstance(node, (str, int, float)):
        return str(node)
    if not isinstance(node, Element):
        raise TypeError(f"Unsupported node type: {type(node)!r}")

    # Host element: string tag
    if isinstance(node.type, str):
        if node.type == "__suspense__":
            from .concurrent import Suspend

            fallback = node.props.get("fallback")
            children = node.props.get("children", ())
            try:
                # For now, expect a single child element.
                child = children[0] if children else None
                return _host_snapshot(child, root, f"{identity_path}.s")
            except Suspend as s:

                def wake() -> None:
                    if root._desired_element is None:
                        return
                    schedule_update_on_root(
                        root, Update(lane=DEFAULT_LANE, payload=root._desired_element)
                    )

                s.thenable.then(wake)
                return _host_snapshot(fallback, root, f"{identity_path}.f")

        children = node.props.get("children", ())
        rendered_children = [
            _host_snapshot(c, root, f"{identity_path}.{i}") for i, c in enumerate(children)
        ]
        return {
            "type": node.type,
            "key": node.key,
            "props": {k: v for k, v in dict(node.props).items() if k != "children"},
            "children": rendered_children,
        }

    # Function/class component
    if callable(node.type):
        ident = f"{identity_path}:{id(node.type)}:{node.key}"
        hooks = root._hooks_by_identity.setdefault(ident, [])
        layout_effects: list[Callable[[], None]] = []
        passive_effects: list[Callable[[], None]] = []

        def schedule_update(lane: Lane) -> None:
            if root._current_element is None:
                return
            schedule_update_on_root(root, Update(lane=lane, payload=root._current_element))

        rendered = _render_component(
            node.type,
            dict(node.props),
            hooks,
            scheduled_layout_effects=layout_effects,
            scheduled_passive_effects=passive_effects,
            schedule_update=schedule_update,
            default_lane=root._current_lane,
        )
        snap = _host_snapshot(rendered, root, identity_path)
        # Commit-ish: layout effects first, then passive effects.
        for run in layout_effects:
            run()
        for run in passive_effects:
            run()
        return snap

    raise TypeError(f"Unsupported element type: {node.type!r}")


def render_to_noop_snapshot(root: Root, element: Element | None) -> Any:
    """Render an element tree to a deterministic host snapshot for tests."""
    return _host_snapshot(element, root, "0")
