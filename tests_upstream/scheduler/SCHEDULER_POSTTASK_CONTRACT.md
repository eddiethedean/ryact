# Scheduler PostTask upstream contract (Milestone 7)

Reference: [`SchedulerPostTask-test.js`](https://github.com/facebook/react/blob/main/packages/scheduler/src/__tests__/SchedulerPostTask-test.js) and [`SchedulerPostTask.js`](https://github.com/facebook/react/blob/main/packages/scheduler/src/forks/SchedulerPostTask.js).

## Python modules

- **Runtime:** [`packages/schedulyr/src/schedulyr/post_task_runtime.py`](../../packages/schedulyr/src/schedulyr/post_task_runtime.py) — `PostTaskMockRuntime`, `TaskController`
- **Harness:** [`packages/schedulyr/src/schedulyr/post_task_scheduler.py`](../../packages/schedulyr/src/schedulyr/post_task_scheduler.py) — `PostTaskSchedulerHarness`
- **Pytest:** [`test_scheduler_posttask_parity.py`](test_scheduler_posttask_parity.py)

## Log vocabulary

- **`Post Task N [priority]`** — `scheduler.postTask` scheduling (`user-blocking`, `user-visible`, `background`, or a single space when undefined).
- **`Task N Fired`** — `flush_tasks` runs the mock task callback with `false`.
- **`Yield N [priority]`** — continuation path when `scheduler.yield` exists (default describe).
- When **`scheduler.yield`** is removed (nested describe), continuations log **`Post Task …`** instead of **`Yield …`**.

## `shouldYield`

Matches fork: `deadline = now + 5` at task entry; **`unstable_shouldYield`** is `now >= deadline`. Continuation tests assert **`shouldYield: false`** with lowercase booleans in logs (see pytest helpers).
