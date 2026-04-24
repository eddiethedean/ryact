# Scheduler setImmediate host contract (Milestone 7)

Reference: [`SchedulerSetImmediate-test.js`](https://github.com/facebook/react/blob/main/packages/scheduler/src/__tests__/SchedulerSetImmediate-test.js) and the **`localSetImmediate`** branch in [`Scheduler.js`](https://github.com/facebook/react/blob/main/packages/scheduler/src/forks/Scheduler.js).

## Python modules

- **Runtime:** [`packages/schedulyr/src/schedulyr/set_immediate_runtime.py`](../../packages/schedulyr/src/schedulyr/set_immediate_runtime.py) — `SetImmediateMockRuntime`
- **Harness:** [`packages/schedulyr/src/schedulyr/set_immediate_scheduler.py`](../../packages/schedulyr/src/schedulyr/set_immediate_scheduler.py) — `SetImmediateSchedulerHarness` (same work loop shape as `BrowserSchedulerHarness`, different macrotask driver)
- **Flags:** [`SchedulerBrowserFlags`](../../packages/schedulyr/src/schedulyr/browser_scheduler.py) — **`gate`** for **`enableAlwaysYieldScheduler`** / **`www`**
- **Pytest:** [`test_scheduler_setimmediate_parity.py`](test_scheduler_setimmediate_parity.py)

## Log vocabulary

- **`Set Immediate`** — host schedules `performWorkUntilDeadline`.
- **`setImmediate Callback`** — `fire_immediate` runs the pending macrotask.
- **`Set Timer`** — `setTimeout` stub (timeouts / unused paths); not asserted in most `it` blocks.

## Top-level smoke

**`does not crash if setImmediate is undefined`** maps to Python: **`schedulyr`** import does not depend on `setImmediate` (see pytest).
