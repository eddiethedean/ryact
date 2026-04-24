# Scheduler fairness / cooperative drain (Milestone 15)

Synthetic **Parity C** contract for the default [`schedulyr.scheduler.Scheduler`](../../packages/schedulyr/src/schedulyr/scheduler.py) (`packages/schedulyr`). Not tied to a single upstream Jest case; see [`test_scheduler_fairness.py`](test_scheduler_fairness.py).

## `run_until_idle(..., max_tasks=...)`

- **`max_tasks=None`** (default): unchanged — drain all runnable work subject to **`time_slice_ms`** and timer **`start_time`**, as before.
- **`max_tasks` is a non-negative `int`**: after that many **callback invocations** (`cb()` runs, including the first half of a continuation before the continuation is re-queued), **`run_until_idle` returns** even if more work remains. Skipped cancelled tasks do **not** count.
- **`max_tasks=0`**: run **no** callbacks in that call — the drain returns before the first **`cb()`** (useful for “yield immediately” probes without advancing **`now`**).
- **Interaction with `time_slice_ms`**: both limits apply; returning when **either** limit trips (after the usual post-callback deadline check).

This models **cooperative chunking** / long-task splitting for embedders without wall-clock fairness (see repo **Non-goals** in [`ROADMAP.md`](../../packages/schedulyr/ROADMAP.md)).
