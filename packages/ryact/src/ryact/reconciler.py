from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Optional

from schedulyr import (
    IDLE_PRIORITY,
    IMMEDIATE_PRIORITY,
    NORMAL_PRIORITY,
    Scheduler,
)


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
DEFAULT_LANE = Lane("default", 2)
IDLE_LANE = Lane("idle", 3)


def lane_to_scheduler_priority(lane: Lane) -> int:
    """Map reconciler lanes to ``schedulyr`` numeric priorities (lower = sooner)."""
    if lane.name == "sync":
        return IMMEDIATE_PRIORITY
    if lane.name == "idle":
        return IDLE_PRIORITY
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
    _flush_task_id: int | None = None
    _commit_fn: Callable[[Any], Any] | None = None


@dataclass
class Update:
    lane: Lane
    payload: Any


def create_root(container_info: Any, scheduler: Optional[Scheduler] = None) -> Root:
    return Root(container_info=container_info, scheduler=scheduler)


def bind_commit(root: Root, commit: Callable[[Any], Any]) -> None:
    """
    Store the host commit callback before ``schedule_update_on_root`` when
    ``root.scheduler`` is set. The scheduler flush invokes ``perform_work`` with
    this callback.
    """

    root._commit_fn = commit


def schedule_update_on_root(root: Root, update: Update) -> None:
    root.pending_updates.append(update)
    if root.scheduler is None:
        return
    if root._commit_fn is None:
        raise RuntimeError(
            "bind_commit() must be called before schedule_update_on_root when root.scheduler is set"
        )
    if root._flush_task_id is not None:
        root.scheduler.cancel_callback(root._flush_task_id)
        root._flush_task_id = None

    def flush() -> None:
        root._flush_task_id = None
        fn = root._commit_fn
        if fn is not None and root.pending_updates:
            perform_work(root, fn)

    priority = lane_to_scheduler_priority(update.lane)
    root._flush_task_id = root.scheduler.schedule_callback(priority, flush, delay_ms=0)


def perform_work(root: Root, render: Callable[[Any], Any]) -> None:
    """
    Extremely early commit model:
    - Process all queued updates in priority order
    - For now, the payload is the root Element to render
    - Delegates actual host rendering to the provided `render` callback
    """

    if not root.pending_updates:
        return

    root.pending_updates.sort(key=lambda u: u.lane.priority)
    last = root.pending_updates[-1]
    root.pending_updates.clear()
    render(last.payload)
