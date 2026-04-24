# schedulyr roadmap

Parity target: **React Scheduler** — `facebook/react` `packages/scheduler` (priorities, delayed work, cooperative execution, and whatever upstream tests assert).

Work is gated by **`tests_upstream/MANIFEST.json`**: scheduler-related rows must stay green in CI. Translated tests live under **`tests_upstream/scheduler/`**; import **`schedulyr`** directly so the suite exercises this package, not only the **`ryact.scheduler`** re-export.

**Consumers:** **`ryact`** re-exports this module as **`ryact.scheduler`** for convenience; **`ryact-testkit.FakeTimers`** supplies deterministic **`now`** for tests.

**Model note:** the default **[`Scheduler`](src/schedulyr/scheduler.py)** uses a **single** min-heap for all work. React’s production fork splits **timer** vs **task** queues, per-priority **expiration**, and host scheduling (**`MessageChannel`**, **`setImmediate`**, **`setTimeout(0)`**, **`scheduler.postTask`**). Milestone **5** — **[`BrowserSchedulerHarness`](src/schedulyr/browser_scheduler.py)** (`MessageChannel`); **6** — **[`UnstableMockScheduler`](src/schedulyr/mock_scheduler.py)** (mock); **7** — **[`PostTaskSchedulerHarness`](src/schedulyr/post_task_scheduler.py)**, **[`SetImmediateSchedulerHarness`](src/schedulyr/set_immediate_scheduler.py)**, **[`SetTimeoutSchedulerHarness`](src/schedulyr/set_timeout_scheduler.py)**; **8** — mock **profiling** buffer + **`unstable_profiling`** (**`SchedulerProfiling-test.js`**). Remaining: **9** (flags, docs, selective dedupe, **`ryact`** map) then **10** (**`Scheduler-test.js`** inventory closure).

---

## Baseline today (implemented sketch)

- **Priority constants** — `IMMEDIATE_PRIORITY` … `IDLE_PRIORITY` (numeric ordering; lower value = runs before higher value when **due times are equal**).
- **`Scheduler`** — injectable **`now`** (defaults to **`time.monotonic`**); min-heap of **`(due, priority, task_id, callback)`** (see [src/schedulyr/scheduler.py](src/schedulyr/scheduler.py)).
- **`schedule_callback`** — returns task **`id`**; callbacks are **`Callable[[], Any]`** (return **`None`** or a **0-arg** continuation callable); **`delay_ms < 0`** is clamped to **`0`**; **`due = now() + delay_ms/1000`**.
- **`cancel_callback(task_id)`** — lazy cancellation (skipped when the task is popped).
- **Continuations** — if a callback **returns** a callable, it is queued as new work (same **priority**, **due** = **`now()`** after the callback).
- **`run_until_idle(time_slice_ms=None)`** — drains **due** work; stops if the next head is not yet due; **`time_slice_ms`** sets a deadline checked **before each task and after each callback**. **`time_slice_ms=0`** means deadline equals **`now()`** at entry, so **no** tasks run until **`now`** moves.
- **`default_scheduler`** — module-level instance (use sparingly in tests; prefer explicit **`Scheduler()`**).

Not in the standalone **[`Scheduler`](src/schedulyr/scheduler.py)** heap (later / broader parity): full **timer vs ready** split for all priorities, starvation / fairness guarantees, **rAF** / **IdleCallback** emulation. **`BrowserSchedulerHarness`** (Milestone 5) implements **MessageChannel**-style macrotasks + **`shouldYield`** / **`requestPaint`** for the **`SchedulerBrowser`** slice only. **`UnstableMockScheduler`** (Milestone 6) implements React’s **`scheduler/unstable_mock`** fork (**virtual time**, explicit flushes, **`log`** / **`waitFor`**-style helpers); Milestone **8** adds opt-in **`enable_profiling`** + **`scheduler_profiling_buffer`**. Milestone **7** adds **`PostTaskMockRuntime`** / **`PostTaskSchedulerHarness`** (**`Post Task`** / **`Task Fired`** / **`Yield`** logs), **`SetImmediateMockRuntime`** / **`SetImmediateSchedulerHarness`** (**`Set Immediate`** / **`setImmediate Callback`**), and **`SetTimeoutSchedulerHarness`** (**`FakeTimers.run_all_pending`**).

**Errors:** if a callback raises, the exception **propagates** out of **`run_until_idle`**; the failed task was already popped and is not re-run; remaining heap work is left for a **subsequent** **`run_until_idle()`** (no “swallow and continue” unless a future manifest test requires it).

---

## Parity slice tracked in CI

| Manifest `id` | Python tests |
|----------------|---------------|
| `scheduler.deterministicFakeTime` | [test_deterministic_fake_time.py](../../tests_upstream/scheduler/test_deterministic_fake_time.py) |
| `scheduler.orderingSemantics` | [test_ordering.py](../../tests_upstream/scheduler/test_ordering.py) |
| `scheduler.delayAndTimeSlice` | [test_delay_time_slice.py](../../tests_upstream/scheduler/test_delay_time_slice.py) |
| `scheduler.cancelAndContinuation` | [test_cancel_continuation.py](../../tests_upstream/scheduler/test_cancel_continuation.py) |
| `scheduler.reentrancy` | [test_reentrancy_and_errors.py](../../tests_upstream/scheduler/test_reentrancy_and_errors.py) |
| `scheduler.browser.SchedulerBrowserParity` | [test_scheduler_browser_parity.py](../../tests_upstream/scheduler/test_scheduler_browser_parity.py) |
| `scheduler.mock.SchedulerMockParity` | [test_scheduler_mock_parity.py](../../tests_upstream/scheduler/test_scheduler_mock_parity.py) |
| `scheduler.mock.SchedulerProfilingParity` | [test_scheduler_profiling_parity.py](../../tests_upstream/scheduler/test_scheduler_profiling_parity.py) |
| `scheduler.fork.SchedulerPostTaskParity` | [test_scheduler_posttask_parity.py](../../tests_upstream/scheduler/test_scheduler_posttask_parity.py) |
| `scheduler.fork.SchedulerSetImmediateParity` | [test_scheduler_setimmediate_parity.py](../../tests_upstream/scheduler/test_scheduler_setimmediate_parity.py) |
| `scheduler.fork.SchedulerSetTimeoutParity` | [test_scheduler_settimeout_parity.py](../../tests_upstream/scheduler/test_scheduler_settimeout_parity.py) |

The first **five** rows exercise **[`Scheduler`](src/schedulyr/scheduler.py)** + **`FakeTimers`** (heap semantics). **`scheduler.browser.SchedulerBrowserParity`** exercises **[`BrowserSchedulerHarness`](src/schedulyr/browser_scheduler.py)** + **[`MockBrowserRuntime`](src/schedulyr/mock_browser_runtime.py)** against upstream **`describe('SchedulerBrowser')`** `assertLog` sequences ([`Scheduler-test.js`](https://github.com/facebook/react/blob/main/packages/scheduler/src/__tests__/Scheduler-test.js)). **`scheduler.mock.SchedulerMockParity`** exercises **[`UnstableMockScheduler`](src/schedulyr/mock_scheduler.py)** against [`SchedulerMock-test.js`](https://github.com/facebook/react/blob/main/packages/scheduler/src/__tests__/SchedulerMock-test.js) (see [`SCHEDULER_MOCK_CONTRACT.md`](../../tests_upstream/scheduler/SCHEDULER_MOCK_CONTRACT.md)). **`scheduler.mock.SchedulerProfilingParity`** exercises **`UnstableMockScheduler(enable_profiling=True)`** against [`SchedulerProfiling-test.js`](https://github.com/facebook/react/blob/main/packages/scheduler/src/__tests__/SchedulerProfiling-test.js) ([`SCHEDULER_PROFILING_CONTRACT.md`](../../tests_upstream/scheduler/SCHEDULER_PROFILING_CONTRACT.md)). **`scheduler.fork.*`** rows cover **[`SchedulerPostTask.js`](https://github.com/facebook/react/blob/main/packages/scheduler/src/forks/SchedulerPostTask.js)**-style and **`Scheduler.js`** **`setImmediate` / `setTimeout`** host paths ([`SCHEDULER_POSTTASK_CONTRACT.md`](../../tests_upstream/scheduler/SCHEDULER_POSTTASK_CONTRACT.md), [`SCHEDULER_SETIMMEDIATE_CONTRACT.md`](../../tests_upstream/scheduler/SCHEDULER_SETIMMEDIATE_CONTRACT.md), [`SCHEDULER_SETTIMEOUT_CONTRACT.md`](../../tests_upstream/scheduler/SCHEDULER_SETTIMEOUT_CONTRACT.md)).

**`ryact-dom` + `schedulyr`:** deferred flush integration is covered by **`react_dom.createRoot.schedulerIntegration`** in **`tests_upstream/MANIFEST.json`** ( **`test_create_root_scheduler_integration.py`** ), not the table above.

---

## Milestone 0 — Harness + manifest alignment **(done)**

- **`tests_upstream/scheduler/`** layout; **`FakeTimers`** + **`schedulyr.Scheduler`** (no **`sleep`**).
- Manifest rows per **`python_test`** file (see table above).

**When you add more parity:** new **`test_*.py`** under **`tests_upstream/scheduler/`**, new **`MANIFEST.json`** row. Heap-style tests keep **`FakeTimers`** + **`Scheduler`**. **`SchedulerBrowser`** uses **`BrowserSchedulerHarness`** + **`MockBrowserRuntime`** (Milestone **5**). **`SchedulerMock-test.js`** uses **`UnstableMockScheduler`** (Milestone **6**). **`SchedulerProfiling-test.js`** uses **`UnstableMockScheduler(enable_profiling=True)`** (Milestone **8**). **PostTask / SetImmediate / SetTimeout** fork tests use Milestone **7** harnesses. Remaining: Milestone **9** (cross-cutting structure), then Milestone **10** (**`pending`** **`Scheduler-test.js`** rows → **`implemented`** / **`non_goal`**).

## Milestone 1 — Core semantics **(done)**

- **Ordering** — same **due**: lower numeric **priority** first; same **(due, priority)**: **FIFO** by monotonic task **id**.
- **Delayed work** — earlier **due** first; negative **`delay_ms`** clamped to immediate.
- **Cooperative yielding** — **`time_slice_ms`** with post-callback deadline check; **`0`** slice behavior documented.
- **Continuations** — return a **0-arg** callable to queue follow-up work.
- **Cancellation** — **`cancel_callback(id)`** with lazy skip on pop.

## Milestone 2 — Edge cases + integration **(re-entrancy + errors done)**

- **Re-entrancy** — **`schedule_callback`** from inside callbacks; multi-level nesting; **cancel** from a callback; **continuation vs nested** order (nested work is pushed before the returned continuation, so same **(due, priority)** it runs first by **task id**).
- **Errors** — callback exceptions **propagate**; remaining tasks stay on the heap for a later **`run_until_idle()`** (see baseline note above).
- **Fairness / starvation** — deferred until manifest-driven translated tests require it.
- **Profiling / tracing** — **`SchedulerProfiling-test.js`** covered by Milestone **8** (**`scheduler.mock.SchedulerProfilingParity`**).

## Milestone 3 — Wire to `ryact` **(optional path done)**

- **`ryact.reconciler.Root`** accepts an optional **`schedulyr.Scheduler`**; **`schedule_update_on_root`** maps **`Lane`** → scheduler priority and schedules a coalesced flush that runs **`perform_work`** (see [`reconciler.py`](../ryact/src/ryact/reconciler.py): **`bind_commit`**, **`lane_to_scheduler_priority`**).
- **`ryact-dom.create_root(container, scheduler=None)`** — default **`None`** keeps synchronous commits; with a **`Scheduler`**, **`Root.render`** only queues work — call **`scheduler.run_until_idle()`** to flush ( **`tests_upstream/react_dom/test_create_root_scheduler_integration.py`**).
- **`schedulyr`** remains independently testable; **`ryact.scheduler`** remains a thin re-export for direct **`schedulyr`** imports in tests.

Further work (still “reconciler matures”): drive **all** host updates through one shared scheduler instance, **lanes** beyond the three constants, and **yield** / interruption semantics per **`packages/ryact/ROADMAP.md`** milestones 3–4.

---

## Upstream test inventory (full parity target)

Full parity means **100% of tests** under React’s [`packages/scheduler/src/__tests__`](https://github.com/facebook/react/tree/main/packages/scheduler/src/__tests__) are **translated** (or explicitly superseded with documented equivalence), **tracked in `MANIFEST.json`**, and **passing** against **`schedulyr`** (plus any required Python host mocks).

| Upstream file | Role (high level) |
|---------------|-------------------|
| [`Scheduler-test.js`](https://github.com/facebook/react/blob/main/packages/scheduler/src/__tests__/Scheduler-test.js) | **`SchedulerBrowser`** + mocked browser globals (`MessageChannel`, `setTimeout`, `performance.now`, …) — largest suite. |
| [`SchedulerMock-test.js`](https://github.com/facebook/react/blob/main/packages/scheduler/src/__tests__/SchedulerMock-test.js) | **`unstable_mock`** — **implemented** via **`scheduler.mock.SchedulerMockParity`** + **[`UnstableMockScheduler`](src/schedulyr/mock_scheduler.py)**. |
| [`SchedulerPostTask-test.js`](https://github.com/facebook/react/blob/main/packages/scheduler/src/__tests__/SchedulerPostTask-test.js) | **`scheduler.postTask`** — **implemented** via **`scheduler.fork.SchedulerPostTaskParity`**. |
| [`SchedulerProfiling-test.js`](https://github.com/facebook/react/blob/main/packages/scheduler/src/__tests__/SchedulerProfiling-test.js) | Profiling / event logging — **implemented** via **`scheduler.mock.SchedulerProfilingParity`**. |
| [`SchedulerSetImmediate-test.js`](https://github.com/facebook/react/blob/main/packages/scheduler/src/__tests__/SchedulerSetImmediate-test.js) | **`setImmediate`** host — **implemented** via **`scheduler.fork.SchedulerSetImmediateParity`**. |
| [`SchedulerSetTimeout-test.js`](https://github.com/facebook/react/blob/main/packages/scheduler/src/__tests__/SchedulerSetTimeout-test.js) | **`setTimeout(0)`** fallback — **implemented** via **`scheduler.fork.SchedulerSetTimeoutParity`**. |

**`Scheduler-test.js`:** the **`SchedulerBrowser`** `it` blocks are covered by **`scheduler.browser.SchedulerBrowserParity`**; **`SchedulerMock-test.js`** by **`scheduler.mock.SchedulerMockParity`**; **`SchedulerProfiling-test.js`** by **`scheduler.mock.SchedulerProfilingParity`**; **PostTask / SetImmediate / SetTimeout** files by **`scheduler.fork.*`**. All other **`describe`** / **`it`** blocks in **`Scheduler-test.js`** (heap semantics, non-browser hosts, **`gate`** branches not yet ported, etc.) remain **`pending`** in **[`upstream_inventory.json`](../../tests_upstream/scheduler/upstream_inventory.json)** until Milestones **9** (structure + shared toggles + optional dedupe) and **10** (inventory closure + manifest).

---

## Milestone 4 — Inventory, traceability, and manifest expansion **(done)**

- **Inventory:** [`tests_upstream/scheduler/upstream_inventory.json`](../../tests_upstream/scheduler/upstream_inventory.json) — one row per upstream **`it` / `it.skip` / `test`**, with stable **`id`**, **`describe_path`**, **`kind`**, **`status`** (`pending` \| `implemented` \| `non_goal`), optional **`manifest_id`** / **`python_test`** (for **`implemented`**), and **`non_goal_rationale`** when **`non_goal`**. The global manifest stays **`implemented`**-only; this file is the full checklist.
- **Extract / regen:** with a local **`facebook/react`** checkout, from the repo root (using [`.venv`](../../README.md) per the root README), run  
  `.venv/bin/python scripts/update_scheduler_upstream_inventory.py /path/to/react`  
  to refresh the JSON after upstream adds or renames tests (merges metadata for unchanged keys).
- **Drift gate:**  
  `.venv/bin/python scripts/check_scheduler_upstream_inventory.py /path/to/react`  
  exits non-zero if the clone contains scheduler **`__tests__`** cases missing from the inventory. CI runs this on a shallow clone (job **`scheduler_upstream_drift`** in [`.github/workflows/ci.yml`](../../.github/workflows/ci.yml)). The older manifest path check remains [`scripts/check_upstream_drift.py`](../../scripts/check_upstream_drift.py).
- **Pytest:** [`tests_upstream/scheduler/test_upstream_inventory_schema.py`](../../tests_upstream/scheduler/test_upstream_inventory_schema.py) enforces schema, unique ids, **`non_goal`** rationale, **`implemented`** → manifest id existence, and that every **`scheduler.browser.*`**, **`scheduler.mock.*`** (including **`SchedulerProfilingParity`**), and **`scheduler.fork.*`** manifest row is backed by at least one **`implemented`** inventory case (legacy heap manifest rows do not require inventory backlinks).
- **Policy:** **`non_goal`** must record **`non_goal_rationale`**; **`implemented`** rows must link **`manifest_id`** + **`python_test`**. Pending cases are tracked only in the inventory until translated.

---

## Milestone 5 — `Scheduler-test.js` host harness (SchedulerBrowser) **(done)**

- **`MockBrowserRuntime`** — [`src/schedulyr/mock_browser_runtime.py`](src/schedulyr/mock_browser_runtime.py): virtual **`performance.now`**, **`MessageChannel`**-style **`Post Message`** / **`fire_message_event`** (logs **`Message Event`**), **`Set Timer`** stubs, optional discrete/continuous event deferral (upstream parity API).
- **`BrowserSchedulerHarness`** — [`src/schedulyr/browser_scheduler.py`](src/schedulyr/browser_scheduler.py): **`Scheduler.js`**-style **`unstable_schedule_callback`**, **`unstable_shouldYield`**, **`unstable_request_paint`**, **`unstable_cancel_callback`**, min-heap task queue + **`frameYieldMs`** / **`normalPriorityTimeout`**-driven yields, continuation macrotasks, and **catch + reschedule** after callback errors (matches **`SchedulerBrowser`** `assertLog` ordering). **`SchedulerBrowserFlags`** mirrors **`SchedulerFeatureFlags`** / Jest **`gate`** for optional branches.
- **Tests** — [`tests_upstream/scheduler/test_scheduler_browser_parity.py`](../../tests_upstream/scheduler/test_scheduler_browser_parity.py) ports all **nine** upstream **`describe('SchedulerBrowser')`** `it` blocks; manifest **`scheduler.browser.SchedulerBrowserParity`** + inventory rows point here. The original **heap-only** modules (**`test_ordering.py`**, etc.) remain for **`schedulyr.Scheduler`** without the browser host; see inventory **`notes`** for the prior manifest mapping.
- **Contract doc** — [`tests_upstream/scheduler/SCHEDULER_BROWSER_CONTRACT.md`](../../tests_upstream/scheduler/SCHEDULER_BROWSER_CONTRACT.md) captures **`assertLog`** sequences and flag defaults.

The standalone **[`Scheduler`](src/schedulyr/scheduler.py)** class is unchanged for consumers that only need the cooperative heap + **`run_until_idle`**.

---

## Milestone 6 — `SchedulerMock-test.js` (`unstable_mock`) **(done)**

**Upstream:** [`SchedulerMock-test.js`](https://github.com/facebook/react/blob/main/packages/scheduler/src/__tests__/SchedulerMock-test.js). All inventory rows for that file are **`implemented`** (see [`upstream_inventory.json`](../../tests_upstream/scheduler/upstream_inventory.json)); manifest **`scheduler.mock.SchedulerMockParity`**.

- **`UnstableMockScheduler`** — [`src/schedulyr/mock_scheduler.py`](src/schedulyr/mock_scheduler.py): port of React **[`SchedulerMock.js`](https://github.com/facebook/react/blob/main/packages/scheduler/src/forks/SchedulerMock.js)** — timer + task min-heaps, **`unstable_advance_time`**, **`unstable_flush_expired`** / **`unstable_flush_all`** / **`unstable_flush_number_of_yields`** / **`unstable_flush_until_next_paint`**, **`unstable_schedule_callback`** with **`options.delay`**, continuations, **`unstable_run_with_priority`** / **`unstable_wrap_callback`**, **`log`**, **`reset`**. API names are **snake_case** on the class (no **`MessageChannel`**; independent of **`BrowserSchedulerHarness`**). Default build keeps **`unstable_profiling`** as **`None`**; **`enable_profiling=True`** enables Milestone **8** (**[`scheduler_profiling_buffer.py`](src/schedulyr/scheduler_profiling_buffer.py)**).
- **Test helpers** — [`tests_upstream/scheduler/mock_scheduler_test_utils.py`](../../tests_upstream/scheduler/mock_scheduler_test_utils.py): synchronous **`assert_log`**, **`wait_for`**, **`wait_for_all`**, **`wait_for_paint`**, **`wait_for_throw`** aligned with React **`internal-test-utils`** + mock flush behavior.
- **Tests** — [`tests_upstream/scheduler/test_scheduler_mock_parity.py`](../../tests_upstream/scheduler/test_scheduler_mock_parity.py): **26** pytest cases (full upstream **`describe`** coverage for that file). **`tests_upstream`** package **`__init__.py`** files enable stable imports.
- **Contract** — [`tests_upstream/scheduler/SCHEDULER_MOCK_CONTRACT.md`](../../tests_upstream/scheduler/SCHEDULER_MOCK_CONTRACT.md).
- **Exports** — **`UnstableMockScheduler`**, **`MockScheduledTask`** from **`schedulyr`** ([`__init__.py`](src/schedulyr/__init__.py)). **`ryact.scheduler`** re-exports for the mock surface remain optional until reconciler tests need them.

---

## Milestone 7 — Host forks: **PostTask**, **SetImmediate**, **SetTimeout** **(done)**

**Upstream:** [`SchedulerPostTask-test.js`](https://github.com/facebook/react/blob/main/packages/scheduler/src/__tests__/SchedulerPostTask-test.js), [`SchedulerSetImmediate-test.js`](https://github.com/facebook/react/blob/main/packages/scheduler/src/__tests__/SchedulerSetImmediate-test.js), [`SchedulerSetTimeout-test.js`](https://github.com/facebook/react/blob/main/packages/scheduler/src/__tests__/SchedulerSetTimeout-test.js). Inventory rows for these paths are **`implemented`** (**28** cases: **11** + **12** + **5**); manifests **`scheduler.fork.SchedulerPostTaskParity`**, **`scheduler.fork.SchedulerSetImmediateParity`**, **`scheduler.fork.SchedulerSetTimeoutParity`**.

- **`PostTaskMockRuntime`** / **`PostTaskSchedulerHarness`** — [`post_task_runtime.py`](src/schedulyr/post_task_runtime.py), [`post_task_scheduler.py`](src/schedulyr/post_task_scheduler.py): **`scheduler.postTask`** / **`scheduler.yield`** (Python uses **`getattr(..., "yield")`** where upstream calls **`scheduler.yield`**), **`TaskController`**, **`flush_tasks`** (not **`MessageChannel`**); nested upstream describe **`delete global.scheduler.yield`** is mirrored by **`remove_yield`** / **`wire_default_yield`**.
- **`SetImmediateMockRuntime`** / **`SetImmediateSchedulerHarness`** — [`set_immediate_runtime.py`](src/schedulyr/set_immediate_runtime.py), [`set_immediate_scheduler.py`](src/schedulyr/set_immediate_scheduler.py): **`BrowserSchedulerHarness`**-shaped cooperative scheduling with **`setImmediate`** macrotasks (**`Set Immediate`** / **`setImmediate Callback`** logs) via **`fire_immediate`**; **`SchedulerBrowserFlags`** covers **`gate`**-style branches (**`www`**, **`enableAlwaysYieldScheduler`**).
- **`SetTimeoutSchedulerHarness`** — [`set_timeout_scheduler.py`](src/schedulyr/set_timeout_scheduler.py): **`SchedulerNoDOM`**-style **`setTimeout(0)`** via injectable **`set_timeout` / `now`**; tests drain with **`FakeTimers.run_all_pending`** ([`fake_timers.py`](../../packages/ryact-testkit/src/ryact_testkit/fake_timers.py)). Includes **SSR** smoke: constructing **`Scheduler`** / **`SetTimeoutSchedulerHarness`** when timers are missing must not raise (see contract).
- **Tests** — [`test_scheduler_posttask_parity.py`](../../tests_upstream/scheduler/test_scheduler_posttask_parity.py) (**11**), [`test_scheduler_setimmediate_parity.py`](../../tests_upstream/scheduler/test_scheduler_setimmediate_parity.py) (**12**), [`test_scheduler_settimeout_parity.py`](../../tests_upstream/scheduler/test_scheduler_settimeout_parity.py) (**5**). Contracts: [`SCHEDULER_POSTTASK_CONTRACT.md`](../../tests_upstream/scheduler/SCHEDULER_POSTTASK_CONTRACT.md), [`SCHEDULER_SETIMMEDIATE_CONTRACT.md`](../../tests_upstream/scheduler/SCHEDULER_SETIMMEDIATE_CONTRACT.md), [`SCHEDULER_SETTIMEOUT_CONTRACT.md`](../../tests_upstream/scheduler/SCHEDULER_SETTIMEOUT_CONTRACT.md).
- **Exports** — **`PostTaskMockRuntime`**, **`TaskController`**, **`PostTaskCallbackNode`**, **`PostTaskSchedulerHarness`**, **`SetImmediateMockRuntime`**, **`SetImmediateSchedulerHarness`**, **`SetTimeoutSchedulerHarness`** from **`schedulyr`** ([`__init__.py`](src/schedulyr/__init__.py)).

---

## Milestone 8 — `SchedulerProfiling-test.js` **(done)**

**Upstream:** [`SchedulerProfiling-test.js`](https://github.com/facebook/react/blob/main/packages/scheduler/src/__tests__/SchedulerProfiling-test.js) ( **`enableProfiling`** + **`scheduler/unstable_mock`** + flamegraph decoder). Inventory rows are **`implemented`** (**9** cases); manifest **`scheduler.mock.SchedulerProfilingParity`**.

- **`SchedulerProfilingBuffer`** / **`ProfilingEventLogger`** — [`scheduler_profiling_buffer.py`](src/schedulyr/scheduler_profiling_buffer.py): growable int32 opcode log (**`1`–`8`**), **`PROFILING_OVERFLOW_MESSAGE`**, optional **`profiling_max_event_log_size`** for fast overflow tests.
- **`UnstableMockScheduler`** — profiling **`mark_*`** call sites mirror upstream **`SchedulerMock.js`** (**`mark_task_start`** on immediate schedule and timer promotion, **`mark_task_run` / `mark_task_yield` / `mark_task_completed` / `mark_task_canceled` / `mark_task_errored`**, **`mark_scheduler_unsuspended` / `mark_scheduler_suspended`** around **`_flush_work`**); **`_MockTask.is_queued`** for cancel semantics.
- **Flamegraph** — [`profiling_flamegraph.py`](../../tests_upstream/scheduler/profiling_flamegraph.py) ports **`stopProfilingAndPrintFlamegraph`** (label column padding + **`🡐`** status markers).
- **Tests** — [`test_scheduler_profiling_parity.py`](../../tests_upstream/scheduler/test_scheduler_profiling_parity.py): **9** pytest cases. Contract: [`SCHEDULER_PROFILING_CONTRACT.md`](../../tests_upstream/scheduler/SCHEDULER_PROFILING_CONTRACT.md).

---

## Milestone 9 — Cross-cutting structure (flags, heap vs harness, **`ryact`**)

**Precondition:** Milestones **5–8** are **(done)** — browser harness, mock + profiling, fork hosts, and inventory rows for those files are green.

**Goal:** one **documented** map of which Python entrypoint owns which upstream surface, plus **shared feature toggles** where inventory already duplicates **`gate`** / **`SchedulerFeatureFlags`** behavior. Still **test-driven**: no new public API unless a translated test or manifest row requires it.

**Out of scope for M9:** porting large batches of remaining **`Scheduler-test.js`** `it` blocks (that is **M10** work). **M9** may add small shared modules or refactors **only** when they unblock M10 or remove real duplication proven by two+ harnesses.

| Track | Deliverables |
|-------|----------------|
| **Flags** | Single module (or clearly layered re-exports) for **`www`**, **`enableAlwaysYieldScheduler`**, and any other flags already mirrored in **`BrowserSchedulerHarness`**, **`SetImmediateSchedulerHarness`**, and mock/profiling tests — avoid three divergent copies of the same default. |
| **Heap `Scheduler`** | Where **mock** or **profiling** tests imply heap invariants (delay, cancel, continuation ordering), add **`tests_upstream/scheduler/`** coverage against **[`scheduler.py`](src/schedulyr/scheduler.py)** first, then align implementation **without** breaking the five heap **`MANIFEST`** rows. |
| **Harness dedupe** | Extract **only** shared helpers (time / priority / continuation bookkeeping) between **`BrowserSchedulerHarness`**, **`UnstableMockScheduler`**, and fork harnesses **when two implementations encode the same rule**; keep separate **host** drivers (MessageChannel vs `setImmediate` vs `postTask` logs) unless tests prove a single class is safe. |
| **`ryact`** | After flags + heap notes are stable: revisit **`lane_to_scheduler_priority`**, **`bind_commit`**, and flush coalescing in [`packages/ryact/src/ryact/reconciler.py`](../ryact/src/ryact/reconciler.py) so deferred roots use the **documented** scheduler entrypoint; prefer **no** behavior change until a failing or new **`tests_upstream`** integration test demands it. |

**Exit criteria (M9):** ROADMAP **Model note** + **Baseline** name the canonical split; flags live in one discoverable place; **M10** can add **`Scheduler-test.js`** parity tests without another flag refactor.

---

## Milestone 10 — Full **`__tests__`** inventory gate (100%)

**Primary gap:** **[`Scheduler-test.js`](https://github.com/facebook/react/blob/main/packages/scheduler/src/__tests__/Scheduler-test.js)** — inventory still lists many **`pending`** cases **outside** **`describe('SchedulerBrowser')`** (other **`describe`** trees, heap-only behavior, additional **`gate`** paths). The other five upstream files under [`__tests__`](https://github.com/facebook/react/tree/main/packages/scheduler/src/__tests__) are already **`implemented`** at the inventory + manifest level (M5–M8).

**Definition:** for **every** row in [`upstream_inventory.json`](../../tests_upstream/scheduler/upstream_inventory.json) whose **`upstream_path`** is under `packages/scheduler/src/__tests__/`, **`status`** is **`implemented`** (with **`manifest_id`** + **`python_test`**) **or** **`non_goal`** with a non-empty **`non_goal_rationale`**. No **`pending`** rows once M10 is **(done)**.

| Step | Action |
|------|--------|
| **1. Translate** | Add pytest (new module(s) or extend existing) per upstream **`it`** / **`test`**, one stable test name per inventory **`id`** where practical. |
| **2. Manifest** | Add or extend **`MANIFEST.json`** rows so each new **`python_test`** file is gated in CI (split rows if one file would exceed ~50 cases — same **`implemented`**-only policy). |
| **3. Inventory** | Flip matching rows to **`implemented`** (or **`non_goal`** with rationale, e.g. Node-only harness not worth porting). |
| **4. Schema** | Extend [`test_upstream_inventory_schema.py`](../../tests_upstream/scheduler/test_upstream_inventory_schema.py) if new **`MANIFEST`** prefixes appear (mirror **`scheduler.browser.*` / `scheduler.mock.*` / `scheduler.fork.*`** coverage rules). |
| **5. Drift** | Keep **[`check_scheduler_upstream_inventory.py`](../../scripts/check_scheduler_upstream_inventory.py)** green; run **[`update_scheduler_upstream_inventory.py`](../../scripts/update_scheduler_upstream_inventory.py)** when React adds or renames cases. |
| **6. Docs** | Mark M10 **(done)** here; refresh **Model note**, **Baseline**, upstream table in this file, and **“100% parity” B** so the final story matches reality (**heap `Scheduler`**, **`BrowserSchedulerHarness`**, **`UnstableMockScheduler`** + optional profiling, fork harnesses). |

**Non-goals (M10):** running the npm **`scheduler`** package in Node; porting **`Scheduler.js`** production forks beyond what translated tests assert.

---

## “100% parity” definitions (two levels)

**A. Current repo gate (today)**  
Every row you already track in **`tests_upstream/MANIFEST.json`** for **`schedulyr`** / scheduler integration is **`implemented`** and passing (heap **`Scheduler`**, **`SchedulerBrowser`**, **`scheduler.mock.*`**, **`scheduler.fork.*`**, plus **`react_dom.createRoot.schedulerIntegration`** where listed).

**B. Full upstream `__tests__` parity (Milestones 4–10)**  
Every inventory row for [`packages/scheduler/src/__tests__`](https://github.com/facebook/react/tree/main/packages/scheduler/src/__tests__) is **`implemented`** or **`non_goal`** (Milestone **10**); Milestone **9** supplies shared flags/docs/dedupe so that closure does not re-open harness drift.

---

## Non-goals (unless the manifest changes)

- **Wall-clock** timing guarantees — semantics remain relative to injected **`now`** and deterministic host mocks (**`FakeTimers`** or the Milestone 5 harness clock), not real OS scheduling jitter.
- **Real browser or Node** execution of upstream **`scheduler`** package — upstream remains the **semantic** reference; the port is validated via translated tests.

**Note:** **Milestone 5** adds **`MockBrowserRuntime`** (**`Post Message` / `Message Event`**) for **`SchedulerBrowser`** parity. **Milestone 6** adds **`UnstableMockScheduler`** for **`unstable_mock`**. **Milestone 7** adds fork hosts (**`PostTask*`**, **`SetImmediate*`**, **`SetTimeout*`** harnesses). **Milestone 8** adds **`enable_profiling`** on the mock scheduler for **`SchedulerProfiling-test.js`**. The default **`Scheduler`** API remains heap-only for embedders that do not need those surfaces.
