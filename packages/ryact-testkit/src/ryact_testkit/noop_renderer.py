from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from ryact.element import Element
from ryact.hooks import _TransitionHook
from ryact.reconciler import (
    DEFAULT_LANE,
    Lane,
    Update,
    bind_commit,
    create_root,
    perform_work,
    render_to_noop_work,
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
            work = render_to_noop_work(self._reconciler_root, payload)
            # Commit phase: publish snapshot then run effects deterministically.
            self.container.last_committed = work.snapshot
            self.container.commits.append(work.snapshot)
            for run in work.insertion_effects:
                run()
            for run in work.layout_effects:
                run()
            for run in work.passive_effects:
                run()
            # Install finished fiber tree for next render.
            if work.finished_work is not None:
                self._reconciler_root.current = work.finished_work
                # Commit-ish: clear transition pending flags after commit.
                cleared = False
                stack: list[Any] = [work.finished_work]
                while stack:
                    f = stack.pop()
                    for h in getattr(f, "hooks", []):
                        if isinstance(h, _TransitionHook):
                            if h.pending:
                                cleared = True
                            h.pending = False
                    sib = getattr(f, "sibling", None)
                    if sib is not None:
                        stack.append(sib)
                    child = getattr(f, "child", None)
                    if child is not None:
                        stack.append(child)
                if cleared:
                    schedule_update_on_root(rr, Update(lane=DEFAULT_LANE, payload=rr._last_element))

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
