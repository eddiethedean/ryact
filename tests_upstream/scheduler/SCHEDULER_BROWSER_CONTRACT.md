# SchedulerBrowser upstream contract (Milestone 5)

Reference: [`packages/scheduler/src/__tests__/Scheduler-test.js`](https://github.com/facebook/react/blob/main/packages/scheduler/src/__tests__/Scheduler-test.js) `describe('SchedulerBrowser')` and [`packages/scheduler/src/forks/Scheduler.js`](https://github.com/facebook/react/blob/main/packages/scheduler/src/forks/Scheduler.js).

## Python modules

- **Host mock:** [`packages/schedulyr/src/schedulyr/mock_browser_runtime.py`](../../packages/schedulyr/src/schedulyr/mock_browser_runtime.py) — `MockBrowserRuntime`
- **Scheduler harness:** [`packages/schedulyr/src/schedulyr/browser_scheduler.py`](../../packages/schedulyr/src/schedulyr/browser_scheduler.py) — `BrowserSchedulerHarness`, `SchedulerBrowserFlags`
- **Pytest:** [`test_scheduler_browser_parity.py`](test_scheduler_browser_parity.py)

## Mock host (`installMockBrowserRuntime`)

- **`performance.now()`** — virtual clock `currentTime` (ms); **`advanceTime(ms)`** / **`resetTime()`** mutate it.
- **`global.setTimeout`** — logs **`Set Timer`** (unused for outcome in the nine tests).
- **`MessageChannel`** — `port2.postMessage()` logs **`Post Message`** and sets a single pending message flag; double post throws.
- **`fireMessageEvent()`** — requires log empty; logs **`Message Event`**; invokes `port1.onmessage` (scheduler’s macrotask); may log **`Discrete Event`** / **`Continuous Event`** if those paths fire (not asserted in the nine `it` blocks).
- **`assertLog` / `isLogEmpty` / `log`** — same semantics as upstream (assert consumes the log).

## Scheduler flags (non-experimental OSS defaults)

From [`SchedulerFeatureFlags.js`](https://github.com/facebook/react/blob/main/packages/scheduler/src/SchedulerFeatureFlags.js):

- **`enableAlwaysYieldScheduler`** — `false` in stable builds (`gate(...)` false in CI).
- **`enableRequestPaint`** — `true`.
- **`frameYieldMs`** — `5` (used by `unstable_shouldYield` vs `startTime` from each macrotask).
- **`normalPriorityTimeout`** — `5000` ms (normal task expiration offset from `startTime`).

## Per-`it` log sequences (stable / `gate` false)

| `it` title | Sequence |
|------------|-----------|
| task that finishes before deadline | `Post Message` → fire → `Message Event`, `Task` |
| task with continuation | `Post Message` → fire → `Message Event`, `Task`, `Yield at 0ms`, `Post Message` → fire → `Message Event`, `Continuation` |
| multiple tasks | `Post Message` → fire → `Message Event`, `A`, `B` |
| multiple tasks with a yield in between | `Post Message` → fire → `Message Event`, `A`, `Post Message` → fire → `Message Event`, `B` |
| cancels tasks | `Post Message` → cancel → fire → `Message Event` |
| throws when a task errors… | `Post Message` → fire throws after `Oops!` → `Message Event`, `Oops!`, `Post Message` → fire → `Message Event`, `Yay` |
| schedule new task after queue has emptied | `Post Message` → fire → `Message Event`, `A` → `Post Message` → fire → `Message Event`, `B` |
| schedule new task after a cancellation | `Post Message` → cancel → fire → `Message Event` → `Post Message` → fire → `Message Event`, `B` |
| yielding continues in a new task… | `Post Message` → fire → `Message Event`, `Original Task`, `shouldYield: false`, `Return a continuation`, `Post Message` → fire → `Message Event`, `Continuation Task` |

When **`enableAlwaysYieldScheduler`** is `true`, upstream expects extra `Post Message` / `Message Event` pairs for **multiple tasks** and **throws** tests; the Python harness exposes flags to match those branches if needed.

## `gate()` in upstream

React’s Jest `gate` flips feature bundles; parity tests default to **stable** (`enableAlwaysYieldScheduler=False`, `www=False`). Optional toggles are supported on `SchedulerBrowserFlags` for future CI matrix rows.
