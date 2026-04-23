# schedulyr roadmap

Parity target: **React Scheduler** — `facebook/react` `packages/scheduler` (priorities, delayed work, cooperative execution, and whatever upstream tests assert).

Work is gated by **`tests_upstream/MANIFEST.json`**: scheduler-related rows must stay green in CI. Translated tests live under **`tests_upstream/scheduler/`**; import **`schedulyr`** directly so the suite exercises this package, not only the **`ryact.scheduler`** re-export.

**Consumers:** **`ryact`** re-exports this module as **`ryact.scheduler`** for convenience; **`ryact-testkit.FakeTimers`** supplies deterministic **`now`** for tests.

**Model note:** the default **[`Scheduler`](src/schedulyr/scheduler.py)** uses a **single** min-heap for all work. React’s production fork splits **timer** vs **task** queues, per-priority **expiration**, and **MessageChannel** host scheduling. Milestone **5** adds **[`BrowserSchedulerHarness`](src/schedulyr/browser_scheduler.py)** for the **`SchedulerBrowser`** slice (separate heap + macrotask / `assertLog` parity); broader parity still grows with translated tests (Milestones **6–10**).

---

## Baseline today (implemented sketch)

- **Priority constants** — `IMMEDIATE_PRIORITY` … `IDLE_PRIORITY` (numeric ordering; lower value = runs before higher value when **due times are equal**).
- **`Scheduler`** — injectable **`now`** (defaults to **`time.monotonic`**); min-heap of **`(due, priority, task_id, callback)`** (see [src/schedulyr/scheduler.py](src/schedulyr/scheduler.py)).
- **`schedule_callback`** — returns task **`id`**; callbacks are **`Callable[[], Any]`** (return **`None`** or a **0-arg** continuation callable); **`delay_ms < 0`** is clamped to **`0`**; **`due = now() + delay_ms/1000`**.
- **`cancel_callback(task_id)`** — lazy cancellation (skipped when the task is popped).
- **Continuations** — if a callback **returns** a callable, it is queued as new work (same **priority**, **due** = **`now()`** after the callback).
- **`run_until_idle(time_slice_ms=None)`** — drains **due** work; stops if the next head is not yet due; **`time_slice_ms`** sets a deadline checked **before each task and after each callback**. **`time_slice_ms=0`** means deadline equals **`now()`** at entry, so **no** tasks run until **`now`** moves.
- **`default_scheduler`** — module-level instance (use sparingly in tests; prefer explicit **`Scheduler()`**).

Not in the standalone **[`Scheduler`](src/schedulyr/scheduler.py)** heap (later / broader parity): full **timer vs ready** split for all priorities, starvation / fairness guarantees, **rAF** / **IdleCallback** emulation. **`BrowserSchedulerHarness`** (Milestone 5) implements **MessageChannel**-style macrotasks + **`shouldYield`** / **`requestPaint`** for the **`SchedulerBrowser`** parity slice only.

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

The first **five** rows exercise **[`Scheduler`](src/schedulyr/scheduler.py)** + **`FakeTimers`** (heap semantics). **`scheduler.browser.SchedulerBrowserParity`** exercises **[`BrowserSchedulerHarness`](src/schedulyr/browser_scheduler.py)** + **[`MockBrowserRuntime`](src/schedulyr/mock_browser_runtime.py)** against upstream **`describe('SchedulerBrowser')`** `assertLog` sequences ([`Scheduler-test.js`](https://github.com/facebook/react/blob/main/packages/scheduler/src/__tests__/Scheduler-test.js)).

**`ryact-dom` + `schedulyr`:** deferred flush integration is covered by **`react_dom.createRoot.schedulerIntegration`** in **`tests_upstream/MANIFEST.json`** ( **`test_create_root_scheduler_integration.py`** ), not the table above.

---

## Milestone 0 — Harness + manifest alignment **(done)**

- **`tests_upstream/scheduler/`** layout; **`FakeTimers`** + **`schedulyr.Scheduler`** (no **`sleep`**).
- Manifest rows per **`python_test`** file (see table above).

**When you add more parity:** new **`test_*.py`** under **`tests_upstream/scheduler/`**, new **`MANIFEST.json`** row. Heap-style tests keep **`FakeTimers`** + **`Scheduler`**. **`SchedulerBrowser`**-style log parity uses **`BrowserSchedulerHarness`** + **`MockBrowserRuntime`** (see Milestone **5**). Other upstream files (**`SchedulerMock-test.js`**, forks, …) still need new modules as milestones land.

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
- **Profiling / tracing** — deferred until manifest-driven tests require it.

## Milestone 3 — Wire to `ryact` **(optional path done)**

- **`ryact.reconciler.Root`** accepts an optional **`schedulyr.Scheduler`**; **`schedule_update_on_root`** maps **`Lane`** → scheduler priority and schedules a coalesced flush that runs **`perform_work`** (see [reconciler.py](src/ryact/reconciler.py): **`bind_commit`**, **`lane_to_scheduler_priority`**).
- **`ryact-dom.create_root(container, scheduler=None)`** — default **`None`** keeps synchronous commits; with a **`Scheduler`**, **`Root.render`** only queues work — call **`scheduler.run_until_idle()`** to flush ( **`tests_upstream/react_dom/test_create_root_scheduler_integration.py`**).
- **`schedulyr`** remains independently testable; **`ryact.scheduler`** remains a thin re-export for direct **`schedulyr`** imports in tests.

Further work (still “reconciler matures”): drive **all** host updates through one shared scheduler instance, **lanes** beyond the three constants, and **yield** / interruption semantics per **`packages/ryact/ROADMAP.md`** milestones 3–4.

---

## Upstream test inventory (full parity target)

Full parity means **100% of tests** under React’s [`packages/scheduler/src/__tests__`](https://github.com/facebook/react/tree/main/packages/scheduler/src/__tests__) are **translated** (or explicitly superseded with documented equivalence), **tracked in `MANIFEST.json`**, and **passing** against **`schedulyr`** (plus any required Python host mocks).

| Upstream file | Role (high level) |
|---------------|-------------------|
| [`Scheduler-test.js`](https://github.com/facebook/react/blob/main/packages/scheduler/src/__tests__/Scheduler-test.js) | **`SchedulerBrowser`** + mocked browser globals (`MessageChannel`, `setTimeout`, `performance.now`, …) — largest suite. |
| [`SchedulerMock-test.js`](https://github.com/facebook/react/blob/main/packages/scheduler/src/__tests__/SchedulerMock-test.js) | **`unstable_mock`** / testing scheduler surface. |
| [`SchedulerPostTask-test.js`](https://github.com/facebook/react/blob/main/packages/scheduler/src/__tests__/SchedulerPostTask-test.js) | **`scheduler`** fork built on **`scheduler.postTask`**. |
| [`SchedulerProfiling-test.js`](https://github.com/facebook/react/blob/main/packages/scheduler/src/__tests__/SchedulerProfiling-test.js) | Profiling / event logging expectations. |
| [`SchedulerSetImmediate-test.js`](https://github.com/facebook/react/blob/main/packages/scheduler/src/__tests__/SchedulerSetImmediate-test.js) | Host path using **`setImmediate`**. |
| [`SchedulerSetTimeout-test.js`](https://github.com/facebook/react/blob/main/packages/scheduler/src/__tests__/SchedulerSetTimeout-test.js) | Host path using **`setTimeout`** fallback. |

**`Scheduler-test.js`:** the **`SchedulerBrowser`** `it` blocks are covered by **`scheduler.browser.SchedulerBrowserParity`**; the rest of that file and the other **`__tests__`** JS modules are tracked in **[`upstream_inventory.json`](../../tests_upstream/scheduler/upstream_inventory.json)** (mostly **`pending`** until Milestones **6–10**). The milestones below close the gap to **full upstream `__tests__` parity**.

---

## Milestone 4 — Inventory, traceability, and manifest expansion **(done)**

- **Inventory:** [`tests_upstream/scheduler/upstream_inventory.json`](../../tests_upstream/scheduler/upstream_inventory.json) — one row per upstream **`it` / `it.skip` / `test`**, with stable **`id`**, **`describe_path`**, **`kind`**, **`status`** (`pending` \| `implemented` \| `non_goal`), optional **`manifest_id`** / **`python_test`** (for **`implemented`**), and **`non_goal_rationale`** when **`non_goal`**. The global manifest stays **`implemented`**-only; this file is the full checklist.
- **Extract / regen:** with a local **`facebook/react`** checkout, from the repo root (using [`.venv`](../../README.md) per the root README), run  
  `.venv/bin/python scripts/update_scheduler_upstream_inventory.py /path/to/react`  
  to refresh the JSON after upstream adds or renames tests (merges metadata for unchanged keys).
- **Drift gate:**  
  `.venv/bin/python scripts/check_scheduler_upstream_inventory.py /path/to/react`  
  exits non-zero if the clone contains scheduler **`__tests__`** cases missing from the inventory. CI runs this on a shallow clone (job **`scheduler_upstream_drift`** in [`.github/workflows/ci.yml`](../../.github/workflows/ci.yml)). The older manifest path check remains [`scripts/check_upstream_drift.py`](../../scripts/check_upstream_drift.py).
- **Pytest:** [`tests_upstream/scheduler/test_upstream_inventory_schema.py`](../../tests_upstream/scheduler/test_upstream_inventory_schema.py) enforces schema, unique ids, **`non_goal`** rationale, **`implemented`** → manifest id existence, and that every **`scheduler.browser.*`** manifest row is backed by at least one **`implemented`** inventory case (legacy heap manifest rows do not require inventory backlinks).
- **Policy:** **`non_goal`** must record **`non_goal_rationale`**; **`implemented`** rows must link **`manifest_id`** + **`python_test`**. Pending cases are tracked only in the inventory until translated.

---

## Milestone 5 — `Scheduler-test.js` host harness (SchedulerBrowser) **(done)**

- **`MockBrowserRuntime`** — [`src/schedulyr/mock_browser_runtime.py`](src/schedulyr/mock_browser_runtime.py): virtual **`performance.now`**, **`MessageChannel`**-style **`Post Message`** / **`fire_message_event`** (logs **`Message Event`**), **`Set Timer`** stubs, optional discrete/continuous event deferral (upstream parity API).
- **`BrowserSchedulerHarness`** — [`src/schedulyr/browser_scheduler.py`](src/schedulyr/browser_scheduler.py): **`Scheduler.js`**-style **`unstable_schedule_callback`**, **`unstable_shouldYield`**, **`unstable_request_paint`**, **`unstable_cancel_callback`**, min-heap task queue + **`frameYieldMs`** / **`normalPriorityTimeout`**-driven yields, continuation macrotasks, and **catch + reschedule** after callback errors (matches **`SchedulerBrowser`** `assertLog` ordering). **`SchedulerBrowserFlags`** mirrors **`SchedulerFeatureFlags`** / Jest **`gate`** for optional branches.
- **Tests** — [`tests_upstream/scheduler/test_scheduler_browser_parity.py`](../../tests_upstream/scheduler/test_scheduler_browser_parity.py) ports all **nine** upstream **`describe('SchedulerBrowser')`** `it` blocks; manifest **`scheduler.browser.SchedulerBrowserParity`** + inventory rows point here. The original **heap-only** modules (**`test_ordering.py`**, etc.) remain for **`schedulyr.Scheduler`** without the browser host; see inventory **`notes`** for the prior manifest mapping.
- **Contract doc** — [`tests_upstream/scheduler/SCHEDULER_BROWSER_CONTRACT.md`](../../tests_upstream/scheduler/SCHEDULER_BROWSER_CONTRACT.md) captures **`assertLog`** sequences and flag defaults.

The standalone **[`Scheduler`](src/schedulyr/scheduler.py)** class is unchanged for consumers that only need the cooperative heap + **`run_until_idle`**.

---

## Milestone 6 — `SchedulerMock-test.js` (`unstable_mock`)

- Translate **`SchedulerMock-test.js`**; add Python API surface equivalent to upstream’s **mock/testing** entry points (`unstable_mock` / related) as required by those tests.
- Add **`ryact.scheduler`** re-exports only if **`ryact`** is the right public seam; otherwise keep **`schedulyr`**-local test-only APIs until **`ryact`** needs them.

---

## Milestone 7 — Host forks: **PostTask**, **SetImmediate**, **SetTimeout**

- **`SchedulerPostTask-test.js`:** emulate **`scheduler.postTask`** scheduling semantics in Python (or document a single supported host profile if upstream splits environments).
- **`SchedulerSetImmediate-test.js`** and **`SchedulerSetTimeout-test.js`:** port tests that depend on those host paths; unify shared **host adapter** code with Milestone 5 where possible.

---

## Milestone 8 — `SchedulerProfiling-test.js`

- Implement **profiling hooks / buffers** (or minimal shims) so translated **`SchedulerProfiling-test.js`** expectations pass.
- Keep profiling **off by default** in production API unless upstream semantics require otherwise.

---

## Milestone 9 — Implementation parity and feature-flag matrix

- Align internal scheduling with **`Scheduler.js`** / fork behavior under **`SchedulerFeatureFlags`**-equivalent toggles **only where tests assert** (avoid speculative flag surface).
- Revisit **`lane_to_scheduler_priority`**, **coalescing**, and **`ryact`** integration so **`schedulyr`** matches upstream ordering and **yield** rules under the full suite.

---

## Milestone 10 — Full **`__tests__`** gate (100%)

- **`MANIFEST.json`** includes **at least one implemented row per upstream `*.js` file** in [`__tests__`](https://github.com/facebook/react/tree/main/packages/scheduler/src/__tests__), and **every** upstream test case in the Milestone 4 checklist is **`implemented`** (or a documented **non-goal** with team sign-off).
- CI runs **`pytest`** on all listed modules; drift scripts validate upstream paths and (optionally) detect new upstream tests.
- Update this ROADMAP: mark Milestones 4–10 **done**; shrink “Model note” / baseline to describe the **final** architecture.

---

## “100% parity” definitions (two levels)

**A. Current repo gate (today)**  
Every row you already track in **`tests_upstream/MANIFEST.json`** for **`schedulyr`** / scheduler integration is **`implemented`** and passing.

**B. Full upstream `__tests__` parity (Milestones 4–10)**  
Every test file under [`packages/scheduler/src/__tests__`](https://github.com/facebook/react/tree/main/packages/scheduler/src/__tests__) is covered per Milestone 10, with **`schedulyr`** (and host mocks) sufficient to run the translated suite with no missing cases except documented **non-goals**.

---

## Non-goals (unless the manifest changes)

- **Wall-clock** timing guarantees — semantics remain relative to injected **`now`** and deterministic host mocks (**`FakeTimers`** or the Milestone 5 harness clock), not real OS scheduling jitter.
- **Real browser or Node** execution of upstream **`scheduler`** package — upstream remains the **semantic** reference; the port is validated via translated tests.

**Note:** **Milestone 5** adds **`MockBrowserRuntime`** ( **`Post Message` / `Message Event`** ) for the **`SchedulerBrowser`** parity tests; the default **`Scheduler`** API remains heap-only for embedders that do not need that host surface.
