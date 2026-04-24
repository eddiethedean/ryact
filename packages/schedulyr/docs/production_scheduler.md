## Production scheduler guide (`schedulyr.production_scheduler`)

### What it is
`schedulyr.production_scheduler` mirrors the production DOM fork’s exported `unstable_*` API surface from upstream React’s `packages/scheduler/src/forks/Scheduler.js`.

This module is useful when you want to embed a Scheduler-like API that matches what React exports in production builds.

### Public surface (high level)
- `unstable_schedule_callback(priority_level, callback, options=None) -> Task`
- `unstable_cancel_callback(task) -> None`
- `unstable_now() -> float` (milliseconds)
- Priority context:
  - `unstable_get_current_priority_level()`
  - `unstable_run_with_priority(priority, fn)`
  - `unstable_next(fn)`
  - `unstable_wrap_callback(fn)`
- Yielding:
  - `unstable_should_yield()`
  - `unstable_request_paint()`
  - `unstable_force_frame_rate(fps)`

### Profiling
If profiling is enabled, `unstable_Profiling` exposes:
- `start_logging_profiling_events()`
- `stop_logging_profiling_events() -> bytes | None`

For expected event sequences and the parity contract, see:
- `tests_upstream/scheduler/SCHEDULER_PRODUCTION_PROFILING_CONTRACT.md`

