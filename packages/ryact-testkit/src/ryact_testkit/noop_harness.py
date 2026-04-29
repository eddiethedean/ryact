from __future__ import annotations

from dataclasses import dataclass

from schedulyr import Scheduler

from .fake_timers import FakeTimers
from .noop_renderer import NoopRoot, create_noop_root


@dataclass(frozen=True)
class NoopRootHarness:
    """
    Convenience bundle for noop roots that need deterministic time control.

    The returned ``Scheduler`` uses ``FakeTimers.now_seconds`` as its clock; tests can
    advance time and then flush scheduled work via ``scheduler.run_until_idle()``.
    """

    timers: FakeTimers
    scheduler: Scheduler
    root: NoopRoot

    def advance(self, ms: int) -> None:
        self.timers.advance(ms)
        self.scheduler.run_until_idle()

    def flush(self) -> None:
        self.scheduler.run_until_idle()


def create_noop_root_harness(*, legacy: bool = False, yield_after_nodes: int | None = None) -> NoopRootHarness:
    timers = FakeTimers()
    sched = Scheduler(now=timers.now_seconds)
    root = create_noop_root(scheduler=sched, legacy=legacy, yield_after_nodes=yield_after_nodes)
    return NoopRootHarness(timers=timers, scheduler=sched, root=root)

