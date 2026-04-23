from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


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


@dataclass
class Update:
    lane: Lane
    payload: Any


def create_root(container_info: Any) -> Root:
    return Root(container_info=container_info)


def schedule_update_on_root(root: Root, update: Update) -> None:
    root.pending_updates.append(update)


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
