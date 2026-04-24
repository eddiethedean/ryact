## Scheduler production profiling contract (Milestone 20)

This contract covers the **production default DOM fork** profiling surface exposed by
`schedulyr.production_scheduler` as `unstable_Profiling`.

### Surface

- `unstable_Profiling.start_logging_profiling_events()`
- `unstable_Profiling.stop_logging_profiling_events() -> bytes | None`

The returned `bytes` value is an `Int32Array`-compatible little-endian stream encoded by
`SchedulerProfilingBuffer`, matching upstream `packages/scheduler/src/SchedulerProfiling.js`.

### Event semantics (when logging is active)

The production scheduler emits the same opcode types as mock profiling:

- Task lifecycle: start / run / yield (continuation) / complete / cancel / error
- Scheduler boundaries: resume/suspend around each executed flush/tick

### Determinism + overflow

- Overflow does **not** print. Instead the production module records
  `PROFILING_OVERFLOW_MESSAGE` into an internal warning list and clears the buffer.
- Tests assert decoded flamegraph output via `profiling_flamegraph.stop_profiling_and_print_flamegraph`.

