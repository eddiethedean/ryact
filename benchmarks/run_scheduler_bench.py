from __future__ import annotations

import argparse
from collections.abc import Callable

import pyperf  # type: ignore[import-untyped]
from schedulyr import NORMAL_PRIORITY, Scheduler


def _mk_scheduler() -> Scheduler:
    # Use the default monotonic now(); pyperf controls process isolation.
    return Scheduler()


def _bench_schedule_only(n: int) -> Callable[[], None]:
    def run() -> None:
        s = _mk_scheduler()
        for _ in range(n):
            s.schedule_callback(NORMAL_PRIORITY, lambda: None, delay_ms=0)

    return run


def _bench_drain_ready(n: int) -> Callable[[], None]:
    def run() -> None:
        s = _mk_scheduler()
        for _ in range(n):
            s.schedule_callback(NORMAL_PRIORITY, lambda: None, delay_ms=0)
        s.run_until_idle()

    return run


def _bench_delayed_then_drain(n: int) -> Callable[[], None]:
    def run() -> None:
        # Deterministic now for delayed-work promotion without sleeping.
        t_ref = [0.0]

        def now() -> float:
            return t_ref[0]

        s = Scheduler(now=now)
        for _ in range(n):
            s.schedule_callback(NORMAL_PRIORITY, lambda: None, delay_ms=10)
        # Advance time past all timers, then drain.
        t_ref[0] = 0.02
        s.run_until_idle()

    return run


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=10_000, help="Number of tasks per run.")
    ns = ap.parse_args()

    runner = pyperf.Runner()
    n = ns.n

    runner.bench_func(f"scheduler.schedule_callback({n})", _bench_schedule_only(n))
    runner.bench_func(f"scheduler.run_until_idle_ready({n})", _bench_drain_ready(n))
    runner.bench_func(f"scheduler.delayed_then_drain({n})", _bench_delayed_then_drain(n))


if __name__ == "__main__":
    main()
