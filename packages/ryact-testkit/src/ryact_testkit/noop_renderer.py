from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from ryact.element import Element
from ryact.reconciler import (
    DEFAULT_LANE,
    Lane,
    Update,
    bind_commit,
    create_root,
    perform_work,
    render_to_noop_snapshot,
    schedule_update_on_root,
)
from schedulyr import Scheduler


@dataclass
class NoopContainer:
    """
    Deterministic in-memory host target for reconciler-focused tests.

    The reconciler commits a *payload* into this container via the root's commit callback.
    Tests can assert on `commits` or on `last_committed`.
    """

    commits: list[Any] = field(default_factory=list)
    last_committed: Any | None = None


@dataclass
class NoopRoot:
    container: NoopContainer
    _reconciler_root: Any

    def render(self, element: Element | None, *, lane: Lane = DEFAULT_LANE) -> None:
        def commit(payload: Any) -> None:
            snap = render_to_noop_snapshot(self._reconciler_root, payload)
            self.container.last_committed = snap
            self.container.commits.append(snap)

        rr = self._reconciler_root
        bind_commit(rr, commit)
        schedule_update_on_root(rr, Update(lane=lane, payload=element))
        if rr.scheduler is None:
            perform_work(rr, commit)

    def flush(self) -> None:
        rr = self._reconciler_root
        fn = rr._commit_fn
        if fn is not None:
            perform_work(rr, fn)


def create_noop_root(*, scheduler: Optional[Scheduler] = None) -> NoopRoot:
    container = NoopContainer()
    rr = create_root(container, scheduler=scheduler)
    return NoopRoot(container=container, _reconciler_root=rr)
