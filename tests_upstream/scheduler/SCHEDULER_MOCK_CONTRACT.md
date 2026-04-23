# Scheduler mock upstream contract (Milestone 6)

Reference: [`packages/scheduler/src/__tests__/SchedulerMock-test.js`](https://github.com/facebook/react/blob/main/packages/scheduler/src/__tests__/SchedulerMock-test.js) with `jest.mock('scheduler', () => require('scheduler/unstable_mock'))`, and React [`SchedulerMock.js`](https://github.com/facebook/react/blob/main/packages/scheduler/src/forks/SchedulerMock.js) (virtual time, `taskQueue` / `timerQueue`, no `MessageChannel`).

## Python modules

- **Mock scheduler:** [`packages/schedulyr/src/schedulyr/mock_scheduler.py`](../../packages/schedulyr/src/schedulyr/mock_scheduler.py) — `UnstableMockScheduler`, `MockScheduledTask`
- **Test helpers:** [`mock_scheduler_test_utils.py`](mock_scheduler_test_utils.py) — `assert_log`, `wait_for`, `wait_for_all`, `wait_for_paint` (sync stand-ins for React `internal-test-utils`)
- **Pytest:** [`test_scheduler_mock_parity.py`](test_scheduler_mock_parity.py)

## Public surface (parity subset)

Mirrors upstream `unstable_*` names in **snake_case** on `UnstableMockScheduler`: `unstable_schedule_callback`, `unstable_cancel_callback`, `unstable_run_with_priority`, `unstable_wrap_callback`, `unstable_get_current_priority_level`, `unstable_should_yield`, `unstable_request_paint`, `unstable_now`, `unstable_advance_time`, `unstable_flush_expired`, `unstable_flush_all`, `unstable_flush_all_without_asserting`, `unstable_flush_number_of_yields`, `unstable_flush_until_next_paint`, `unstable_has_pending_work`, `unstable_clear_log`, `log`, `reset`.

Priority constants match React (`unstable_ImmediatePriority` … `unstable_IdlePriority` via `schedulyr` re-exports).

## Log strings

Upstream Jest logs use lowercase `"true"` / `"false"` for booleans in template strings; parity tests use the same for `shouldYield` and `did timeout` lines.

## Manifest

Inventory cases for `SchedulerMock-test.js` use **`manifest_id`:** `scheduler.mock.SchedulerMockParity` → [`test_scheduler_mock_parity.py`](test_scheduler_mock_parity.py).
