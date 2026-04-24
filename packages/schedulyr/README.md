# schedulyr

[![PyPI](https://img.shields.io/pypi/v/schedulyr.svg)](https://pypi.org/project/schedulyr/)
[![Python](https://img.shields.io/pypi/pyversions/schedulyr.svg)](https://pypi.org/project/schedulyr/)
[![CI](https://github.com/eddiethedean/ryact/actions/workflows/ci.yml/badge.svg)](https://github.com/eddiethedean/ryact/actions/workflows/ci.yml)

Python port of **React Scheduler** semantics (parity target: `facebook/react` `packages/scheduler`).

## Install

```bash
pip install schedulyr
```

## Tiny example

```python
from schedulyr import NORMAL_PRIORITY, Scheduler

s = Scheduler()
s.schedule_callback(NORMAL_PRIORITY, lambda: print("work"), delay_ms=0)
s.run_until_idle()
```

## Semantics (Milestone 1)

- **`cancel_callback(task_id)`** — marks a scheduled task as cancelled; it is skipped when popped (ids come from **`schedule_callback`** return values).
- **Continuations** — a callback may **return** another callable; it is queued with the same priority and **due** immediately after **`now()`** (return **`None`** or use a plain **`lambda: None`** when finished).
- **`delay_ms`** — values **< 0** are treated as **0**.
- **`run_until_idle(time_slice_ms=...)`** — optional time budget checked between tasks and after each callback; **`time_slice_ms=0`** yields before running work unless **`now`** changes first.

## Semantics (Milestone 2)

- **Re-entrancy** — you may call **`schedule_callback`** from inside a running task; the heap stays consistent (see upstream parity tests under **`tests_upstream/scheduler/`**).
- **Errors** — if a task raises, the exception leaves **`run_until_idle`** immediately; call **`run_until_idle()`** again to drain remaining tasks (React-style “log and continue” is not implemented unless parity tests demand it later).

## Browser host slice (Milestone 5)

- **`MockBrowserRuntime`** / **`BrowserSchedulerHarness`** — same module exports as **`from schedulyr import ...`**: MessageChannel-style **`Post Message`** / **`Message Event`** logs, **`unstable_shouldYield`**, **`unstable_request_paint`**, continuation macrotasks, and error rescheduling aligned with **`SchedulerBrowser`** in upstream **`Scheduler-test.js`** (see **`tests_upstream/scheduler/test_scheduler_browser_parity.py`**).

## Jest unstable_mock slice (Milestone 6)

- **`UnstableMockScheduler`** — virtual-time port of React **`SchedulerMock.js`**: **`unstable_advance_time`**, **`unstable_flush_expired`** / **`unstable_flush_all`**, **`unstable_flush_number_of_yields`**, **`unstable_flush_until_next_paint`**, delayed **`options.delay`**, immediate queue, and **`log`** for **`SchedulerMock-test.js`** parity (see **`tests_upstream/scheduler/test_scheduler_mock_parity.py`** and **`tests_upstream/scheduler/SCHEDULER_MOCK_CONTRACT.md`**).
- **Profiling (Milestone 8)** — pass **`enable_profiling=True`** for **`unstable_profiling.start_logging_profiling_events`** / **`stop_logging_profiling_events`** and the **`SchedulerProfiling.js`** opcode stream; see **`tests_upstream/scheduler/test_scheduler_profiling_parity.py`** and [`SCHEDULER_PROFILING_CONTRACT.md`](../../tests_upstream/scheduler/SCHEDULER_PROFILING_CONTRACT.md).

## Host fork slices (Milestone 7)

- **`PostTaskSchedulerHarness`** + **`PostTaskMockRuntime`** — **`SchedulerPostTask-test.js`** (`scheduler.postTask` / `yield`; [`SCHEDULER_POSTTASK_CONTRACT.md`](../../tests_upstream/scheduler/SCHEDULER_POSTTASK_CONTRACT.md)).
- **`SetImmediateSchedulerHarness`** + **`SetImmediateMockRuntime`** — **`SchedulerSetImmediate-test.js`** ([`SCHEDULER_SETIMMEDIATE_CONTRACT.md`](../../tests_upstream/scheduler/SCHEDULER_SETIMMEDIATE_CONTRACT.md)).
- **`SetTimeoutSchedulerHarness`** — **`SchedulerSetTimeout-test.js`** with **`FakeTimers.run_all_pending`** ([`SCHEDULER_SETTIMEOUT_CONTRACT.md`](../../tests_upstream/scheduler/SCHEDULER_SETTIMEOUT_CONTRACT.md)).

## Source of truth

- Upstream: `https://github.com/facebook/react/tree/main/packages/scheduler`

