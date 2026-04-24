# Scheduler profiling parity contract

Python parity targets [`SchedulerProfiling-test.js`](https://github.com/facebook/react/blob/main/packages/scheduler/src/__tests__/SchedulerProfiling-test.js) when React is built with **`enableProfiling`** (the suite mocks **`scheduler`** with **`scheduler/unstable_mock`**).

## Harness

- **`UnstableMockScheduler(enable_profiling=True)`** — same mock heaps and flush API as Milestone 6, plus **`unstable_profiling.start_logging_profiling_events`** / **`stop_logging_profiling_events`** and the **`mark*`** hooks aligned with upstream [`SchedulerProfiling.js`](https://github.com/facebook/react/blob/main/packages/scheduler/src/SchedulerProfiling.js) and [`SchedulerMock.js`](https://github.com/facebook/react/blob/main/packages/scheduler/src/forks/SchedulerMock.js).
- **`unstable_profiling`** is **`None`** when **`enable_profiling=False`** (default), matching a non-profiling **`scheduler`** build.
- **`profiling_max_event_log_size`** — optional cap on the int32 slot count (defaults to upstream **`524288`**). The overflow test uses a **tiny** cap so the auto-stop path runs quickly.

## Event log

Opcodes (**`Int32Array`** / little-endian **`int32`** payload): **`1`** TaskStart, **`2`** TaskComplete, **`3`** TaskError, **`4`** TaskCancel, **`5`** TaskRun, **`6`** TaskYield, **`7`** SchedulerSuspend, **`8`** SchedulerResume. Times are **microseconds** (**`ms * 1000`** from mock time).

## Flamegraph string

[`profiling_flamegraph.stop_profiling_and_print_flamegraph`](profiling_flamegraph.py) mirrors the Jest **`stopProfilingAndPrintFlamegraph`** helper (including **30-column** label padding and the **`🡐`** status suffixes). An empty written log still decodes to the single main-thread row (leading **`0`** opcode), matching a zero-filled upstream buffer.

## Overflow

When the log would exceed **`profiling_max_event_log_size`**, the buffer clears, **`PROFILING_OVERFLOW_MESSAGE`** is recorded on the scheduler (**`_profiling_warnings`**), and **`stop_logging_profiling_events`** yields an empty profile until logging is restarted.
