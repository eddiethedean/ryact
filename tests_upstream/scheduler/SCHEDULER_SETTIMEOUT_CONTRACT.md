# Scheduler setTimeout / NoDOM contract (Milestone 7)

Reference: [`SchedulerSetTimeout-test.js`](https://github.com/facebook/react/blob/main/packages/scheduler/src/__tests__/SchedulerSetTimeout-test.js).

## Python modules

- **Harness:** [`packages/schedulyr/src/schedulyr/set_timeout_scheduler.py`](../../packages/schedulyr/src/schedulyr/set_timeout_scheduler.py) — `SetTimeoutSchedulerHarness` (`setTimeout(0)` + **`FakeTimers.run_all_pending`**)
- **Timers:** [`ryact_testkit.FakeTimers`](../../packages/ryact-testkit/src/ryact_testkit/fake_timers.py) — **`run_all_pending`** added for **`jest.runAllTimers`**-style drains
- **Pytest:** [`test_scheduler_settimeout_parity.py`](test_scheduler_settimeout_parity.py)

## SSR-style checks

Upstream verifies `require('scheduler')` when globals are missing. Python parity asserts **`schedulyr`** import and **`Scheduler()`** construction do not require host timers at import time.
