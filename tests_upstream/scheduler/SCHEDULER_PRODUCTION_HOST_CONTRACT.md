## Scheduler production host loop contract (Milestone 19)

This contract covers the **default DOM fork** host semantics from upstream `packages/scheduler/src/forks/Scheduler.js`:

- **Driver selection**: prefer `setImmediate`, else `MessageChannel`, else `setTimeout(0)`
- **Host tick loop**: `performWorkUntilDeadline` schedules the next host task if more work remains
- **Yield signals**:
  - time-slice: yield once elapsed time exceeds `frameYieldMs`
  - requestPaint: if `enableRequestPaint` and `requestPaint()` was called during a tick, yield before running more work
  - continuation: a task that returns a continuation forces a host-yield (continuation runs on a subsequent host tick)

### Deterministic host fakes + log strings

The tests use deterministic Python fakes that mirror upstream log strings:

- **setImmediate driver** (`SetImmediateMockRuntime`)
  - schedule: `Set Immediate`
  - tick: `setImmediate Callback`
- **MessageChannel driver** (`MockBrowserRuntime`)
  - schedule: `Post Message`
  - tick: `Message Event`
- **setTimeout(0) driver** (`SetTimeoutMockRuntime`)
  - schedule: `Set Timer`
  - tick: `SetTimeout Callback`

### Observable assertions

The contract is asserted by `tests_upstream/scheduler/test_scheduler_production_host_loop.py`:

- **selection order** via which schedule log is emitted
- **yield** via observing that only the first task runs in a tick and the host schedules a second tick (`Post Message` / `Set Immediate` / `Set Timer`)

