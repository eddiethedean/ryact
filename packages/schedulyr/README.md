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

## Source of truth

- Upstream: `https://github.com/facebook/react/tree/main/packages/scheduler`

