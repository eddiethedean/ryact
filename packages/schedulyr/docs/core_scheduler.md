## Core scheduler guide (`schedulyr.Scheduler`)

### What it is
`schedulyr.Scheduler` is a deterministic cooperative scheduler: you enqueue callbacks with priorities and (optional) delays, then explicitly drain work with `run_until_idle()`.

It is designed to mirror the semantic core of React’s scheduler queues (timers → tasks ordered by expiration) while remaining easy to embed in Python code.

### Basic usage

```python
from schedulyr import NORMAL_PRIORITY, Scheduler

s = Scheduler()
s.schedule_callback(NORMAL_PRIORITY, lambda: print("work"))
s.run_until_idle()
```

### Key APIs
- `schedule_callback(priority, callback, delay_ms=0) -> int`
  - Returns a task id (an int).
  - `delay_ms < 0` is clamped to `0`.
- `cancel_callback(task_id) -> None`
  - Lazy cancel: cancelled tasks are skipped when popped.
- `run_until_idle(time_slice_ms=None, *, max_tasks=None) -> None`
  - Drain ready work until there are no ready tasks, or you hit `time_slice_ms` / `max_tasks`.
  - `time_slice_ms=0` / `max_tasks=0` can be used to “yield” without running tasks.

### Continuations
If a scheduled callback returns another 0-arg callable, it is treated as a continuation and is queued as new work with the same priority.

### Deterministic time
For tests, inject a deterministic clock:

```python
from ryact_testkit import FakeTimers
from schedulyr import NORMAL_PRIORITY, Scheduler

timers = FakeTimers()
s = Scheduler(now=timers.now_seconds)
```

