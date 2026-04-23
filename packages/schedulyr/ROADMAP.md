# schedulyr roadmap

Parity target: **React Scheduler** — `facebook/react` `packages/scheduler` (priorities, delayed work, cooperative execution, and whatever upstream tests assert).

Work is gated by **`tests_upstream/MANIFEST.json`**: scheduler-related rows must stay green in CI. Translated tests live under **`tests_upstream/scheduler/`**; import **`schedulyr`** directly so the suite exercises this package, not only the **`ryact.scheduler`** re-export.

**Consumers:** **`ryact`** re-exports this module as **`ryact.scheduler`** for convenience; **`ryact-testkit.FakeTimers`** supplies deterministic **`now`** for tests.

**Model note:** the default **[`Scheduler`](src/schedulyr/scheduler.py)** uses a **single** min-heap for all work. React’s production fork splits **timer** vs **task** queues, per-priority **expiration**, and **MessageChannel** host scheduling. Milestone **5** adds **[`BrowserSchedulerHarness`](src/schedulyr/browser_scheduler.py)** for the **`SchedulerBrowser`** slice; Milestone **6** adds **[`UnstableMockScheduler`](src/schedulyr/mock_scheduler.py)** for **`scheduler/unstable_mock`** (virtual time + `waitFor` / `assertLog`-style helpers). Broader parity still grows with Milestones **7–10**.

---

## Baseline today (implemented sketch)

- **Priority constants** — `IMMEDIATE_PRIORITY` … `IDLE_PRIORITY` (numeric ordering; lower value = runs before higher value when **due times are equal**).
- **`Scheduler`** — injectable **`now`** (defaults to **`time.monotonic`**); min-heap of **`(due, priority, task_id, callback)`** (see [src/schedulyr/scheduler.py](src/schedulyr/scheduler.py)).
- **`schedule_callback`** — returns task **`id`**; callbacks are **`Callable[[], Any]`** (return **`None`** or a **0-arg** continuation callable); **`delay_ms < 0`** is clamped to **`0`**; **`due = now() + delay_ms/1000`**.
- **`cancel_callback(task_id)`** — lazy cancellation (skipped when the task is popped).
- **Continuations** — if a callback **returns** a callable, it is queued as new work (same **priority**, **due** = **`now()`** after the callback).
- **`run_until_idle(time_slice_ms=None)`** — drains **due** work; stops if the next head is not yet due; **`time_slice_ms`** sets a deadline checked **before each task and after each callback**. **`time_slice_ms=0`** means deadline equals **`now()`** at entry, so **no** tasks run until **`now`** moves.
- **`default_scheduler`** — module-level instance (use sparingly in tests; prefer explicit **`Scheduler()`**).

Not in the standalone **[`Scheduler`](src/schedulyr/scheduler.py)** heap (later / broader parity): full **timer vs ready** split for all priorities, starvation / fairness guarantees, **rAF** / **IdleCallback** emulation. **`BrowserSchedulerHarness`** (Milestone 5) implements **MessageChannel**-style macrotasks + **`shouldYield`** / **`requestPaint`** for the **`SchedulerBrowser`** slice only. **`UnstableMockScheduler`** (Milestone 6) implements React’s **`scheduler/unstable_mock`** fork (**virtual time**, explicit flushes, **`log`** / **`waitFor`**-style helpers) for [`SchedulerMock-test.js`](https://github.com/facebook/react/blob/main/packages/scheduler/src/__tests__/SchedulerMock-test.js) — separate from both the heap API and the browser harness.

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

The first **five** rows exercise **[`Scheduler`](src/schedulyr/scheduler.py)** + **`FakeTimers`** (heap semantics). **`scheduler.browser.SchedulerBrowserParity`** exercises **[`BrowserSchedulerHarness`](src/schedulyr/browser_scheduler.py)** + **[`MockBrowserRuntime`](src/schedulyr/mock_browser_runtime.py)** against upstream **`describe('SchedulerBrowser')`** `assertLog` sequences ([`Scheduler-test.js`](https://github.com/facebook/react/blob/main/packages/scheduler/src/__tests__/Scheduler-test.js)). **`scheduler.mock.SchedulerMockParity`** exercises **[`UnstableMockScheduler`](src/schedulyr/mock_scheduler.py)** against [`SchedulerMock-test.js`](https://github.com/facebook/react/blob/main/packages/scheduler/src/__tests__/SchedulerMock-test.js) (see [`SCHEDULER_MOCK_CONTRACT.md`](../../tests_upstream/scheduler/SCHEDULER_MOCK_CONTRACT.md)).

**`ryact-dom` + `schedulyr`:** deferred flush integration is covered by **`react_dom.createRoot.schedulerIntegration`** in **`tests_upstream/MANIFEST.json`** ( **`test_create_root_scheduler_integration.py`** ), not the table above.

---

## Milestone 0 — Harness + manifest alignment **(done)**

- **`tests_upstream/scheduler/`** layout; **`FakeTimers`** + **`schedulyr.Scheduler`** (no **`sleep`**).
- Manifest rows per **`python_test`** file (see table above).

**When you add more parity:** new **`test_*.py`** under **`tests_upstream/scheduler/`**, new **`MANIFEST.json`** row. Heap-style tests keep **`FakeTimers`** + **`Scheduler`**. **`SchedulerBrowser`**-style log parity uses **`BrowserSchedulerHarness`** + **`MockBrowserRuntime`** (Milestone **5**). **`SchedulerMock-test.js`** uses **`UnstableMockScheduler`** (Milestone **6**). Remaining upstream files (forks, profiling, …) still need new modules as milestones land.

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
| [`SchedulerMock-test.js`](https://github.com/facebook/react/blob/main/packages/scheduler/src/__tests__/SchedulerMock-test.js) | **`unstable_mock`** — **implemented** via **`scheduler.mock.SchedulerMockParity`** + **[`UnstableMockScheduler`](src/schedulyr/mock_scheduler.py)**. |
| [`SchedulerPostTask-test.js`](https://github.com/facebook/react/blob/main/packages/scheduler/src/__tests__/SchedulerPostTask-test.js) | **`scheduler`** fork built on **`scheduler.postTask`**. |
| [`SchedulerProfiling-test.js`](https://github.com/facebook/react/blob/main/packages/scheduler/src/__tests__/SchedulerProfiling-test.js) | Profiling / event logging expectations. |
| [`SchedulerSetImmediate-test.js`](https://github.com/facebook/react/blob/main/packages/scheduler/src/__tests__/SchedulerSetImmediate-test.js) | Host path using **`setImmediate`**. |
| [`SchedulerSetTimeout-test.js`](https://github.com/facebook/react/blob/main/packages/scheduler/src/__tests__/SchedulerSetTimeout-test.js) | Host path using **`setTimeout`** fallback. |

**`Scheduler-test.js`:** the **`SchedulerBrowser`** `it` blocks are covered by **`scheduler.browser.SchedulerBrowserParity`**; **`SchedulerMock-test.js`** is covered by **`scheduler.mock.SchedulerMockParity`**. The rest of **`Scheduler-test.js`** and the other **`__tests__`** JS modules are tracked in **[`upstream_inventory.json`](../../tests_upstream/scheduler/upstream_inventory.json)** (mostly **`pending`** until Milestones **7–10**). The milestones below close the gap to **full upstream `__tests__` parity**.

---

## Milestone 4 — Inventory, traceability, and manifest expansion **(done)**

- **Inventory:** [`tests_upstream/scheduler/upstream_inventory.json`](../../tests_upstream/scheduler/upstream_inventory.json) — one row per upstream **`it` / `it.skip` / `test`**, with stable **`id`**, **`describe_path`**, **`kind`**, **`status`** (`pending` \| `implemented` \| `non_goal`), optional **`manifest_id`** / **`python_test`** (for **`implemented`**), and **`non_goal_rationale`** when **`non_goal`**. The global manifest stays **`implemented`**-only; this file is the full checklist.
- **Extract / regen:** with a local **`facebook/react`** checkout, from the repo root (using [`.venv`](../../README.md) per the root README), run  
  `.venv/bin/python scripts/update_scheduler_upstream_inventory.py /path/to/react`  
  to refresh the JSON after upstream adds or renames tests (merges metadata for unchanged keys).
- **Drift gate:**  
  `.venv/bin/python scripts/check_scheduler_upstream_inventory.py /path/to/react`  
  exits non-zero if the clone contains scheduler **`__tests__`** cases missing from the inventory. CI runs this on a shallow clone (job **`scheduler_upstream_drift`** in [`.github/workflows/ci.yml`](../../.github/workflows/ci.yml)). The older manifest path check remains [`scripts/check_upstream_drift.py`](../../scripts/check_upstream_drift.py).
- **Pytest:** [`tests_upstream/scheduler/test_upstream_inventory_schema.py`](../../tests_upstream/scheduler/test_upstream_inventory_schema.py) enforces schema, unique ids, **`non_goal`** rationale, **`implemented`** → manifest id existence, and that every **`scheduler.browser.*`** and **`scheduler.mock.*`** manifest row is backed by at least one **`implemented`** inventory case (legacy heap manifest rows do not require inventory backlinks).
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

- **`UnstableMockScheduler`** — [`src/schedulyr/mock_scheduler.py`](src/schedulyr/mock_scheduler.py): port of React **[`SchedulerMock.js`](https://github.com/facebook/react/blob/main/packages/scheduler/src/forks/SchedulerMock.js)** — timer + task min-heaps, **`unstable_advance_time`**, **`unstable_flush_expired`** / **`unstable_flush_all`** / **`unstable_flush_number_of_yields`** / **`unstable_flush_until_next_paint`**, **`unstable_schedule_callback`** with **`options.delay`**, continuations, **`unstable_run_with_priority`** / **`unstable_wrap_callback`**, **`log`**, **`reset`**. API names are **snake_case** on the class (no **`MessageChannel`**; independent of **`BrowserSchedulerHarness`**). Profiling hooks omitted (matches non-profiling upstream test bundle).
- **Test helpers** — [`tests_upstream/scheduler/mock_scheduler_test_utils.py`](../../tests_upstream/scheduler/mock_scheduler_test_utils.py): synchronous **`assert_log`**, **`wait_for`**, **`wait_for_all`**, **`wait_for_paint`** aligned with React **`internal-test-utils`** + mock flush behavior.
- **Tests** — [`tests_upstream/scheduler/test_scheduler_mock_parity.py`](../../tests_upstream/scheduler/test_scheduler_mock_parity.py): **26** pytest cases (full upstream **`describe`** coverage for that file). **`tests_upstream`** package **`__init__.py`** files enable stable imports.
- **Contract** — [`tests_upstream/scheduler/SCHEDULER_MOCK_CONTRACT.md`](../../tests_upstream/scheduler/SCHEDULER_MOCK_CONTRACT.md).
- **Exports** — **`UnstableMockScheduler`**, **`MockScheduledTask`** from **`schedulyr`** ([`__init__.py`](src/schedulyr/__init__.py)). **`ryact.scheduler`** re-exports for the mock surface remain optional until reconciler tests need them.

---

## Milestone 7 — Host forks: **PostTask**, **SetImmediate**, **SetTimeout**

**Upstream:** [`SchedulerPostTask-test.js`](https://github.com/facebook/react/blob/main/packages/scheduler/src/__tests__/SchedulerPostTask-test.js), [`SchedulerSetImmediate-test.js`](https://github.com/facebook/react/blob/main/packages/scheduler/src/__tests__/SchedulerSetImmediate-test.js), [`SchedulerSetTimeout-test.js`](https://github.com/facebook/react/blob/main/packages/scheduler/src/__tests__/SchedulerSetTimeout-test.js).

- **Shared host:** grow **[`MockBrowserRuntime`](src/schedulyr/mock_browser_runtime.py)** (or a small **`schedulyr/host_config.py`**) so **`setTimeout` / `clearTimeout`**, **`setImmediate`**, and **`scheduler.postTask`** (where applicable) match the **event logs** each fork’s tests expect — reuse the Milestone **5** “log then **`fire_message_event`**” discipline where the upstream tests use the same mock style.
- **Harness:** either additional **`BrowserSchedulerHarness`** modes / subclasses **or** dedicated thin harnesses per fork — keep **`Scheduler.js`**-aligned branching (**`MessageChannel` vs `setImmediate` vs `setTimeout`**) **only** as far as translated tests require (avoid porting unused fork paths).
- **Tests + gate:** one or more **`MANIFEST.json`** rows per file (or one row per logical pytest module); update **[`upstream_inventory.json`](../../tests_upstream/scheduler/upstream_inventory.json)**; run **[`check_scheduler_upstream_inventory.py`](../../scripts/check_scheduler_upstream_inventory.py)** after regen.

---

## Milestone 8 — `SchedulerProfiling-test.js`

**Upstream:** [`SchedulerProfiling-test.js`](https://github.com/facebook/react/blob/main/packages/scheduler/src/__tests__/SchedulerProfiling-test.js) ( **`enableProfiling`** / **`Scheduler.unstable_Profiling`** branches).

- **Shim first:** implement **`unstable_Profiling.startLoggingProfilingEvents` / `stopLoggingProfilingEvents`** (or no-ops where upstream expects **`null`** when profiling is off) so **`if (!enableProfiling)`** early-return tests pass unchanged.
- **Buffers:** when **`enableProfiling`** is on in tests, record the **Int32Array**-style event stream the flamegraph tests assert; keep the default package build **profiling-off** unless manifest tests require otherwise.
- **Tests + inventory:** new pytest module(s), **`MANIFEST.json`** row(s), inventory **`implemented`** / **`non_goal`** with rationale for any case that stays unported.

---

## Milestone 9 — Cross-cutting parity (flags, heap vs harness, **`ryact`**)

**Goal:** after Milestones **6–8**, reconcile **one** coherent story for production-style **`Scheduler`** vs test harnesses — still **test-driven**, no speculative API.

- **Flags:** centralize **`SchedulerBrowserFlags`**-style toggles (or fold into one **`SchedulerFeatureFlags`**-shaped module) so **`gate(...)`** / **`SchedulerFeatureFlags.js`** branches used across **Browser**, **Mock**, and **Profiling** tests have a **single** Python source of truth.
- **`Scheduler` (heap):** align **[`scheduler.py`](src/schedulyr/scheduler.py)** with any semantics the **mock** / **profiling** suites prove must hold for embedders (e.g. delay / cancel / continuation edge cases) **without** breaking existing **`FakeTimers`** manifest rows — extend tests before changing behavior.
- **`BrowserSchedulerHarness`:** deduplicate duplicated logic with new mock / fork code from M6–8; document which entrypoint (**`Scheduler`** vs **`BrowserSchedulerHarness`** vs mock-only API) **`ryact`** should call for deferred work.
- **`ryact`:** revisit **`lane_to_scheduler_priority`**, **`bind_commit`**, and coalescing in [`packages/ryact/src/ryact/reconciler.py`](../ryact/src/ryact/reconciler.py) once scheduler tests pin ordering / yield expectations end-to-end.

---

## Milestone 10 — Full **`__tests__`** gate (100%)

**Definition:** every **`it` / `it.skip` / `test`** listed in [`upstream_inventory.json`](../../tests_upstream/scheduler/upstream_inventory.json) for all six scheduler **`__tests__`** files is **`implemented`** with passing pytest **or** **`non_goal`** with **`non_goal_rationale`**; no silent gaps.

- **`MANIFEST.json`:** at least **one** **`implemented`** row per upstream **`*.js`** file under [`__tests__`](https://github.com/facebook/react/tree/main/packages/scheduler/src/__tests__) (may be one coarse id per file or split rows — same **`implemented`**-only gate as today).
- **Drift:** **[`check_scheduler_upstream_inventory.py`](../../scripts/check_scheduler_upstream_inventory.py)** stays green on CI’s shallow **`facebook/react`** clone; re-run **[`update_scheduler_upstream_inventory.py`](../../scripts/update_scheduler_upstream_inventory.py)** when upstream adds cases.
- **Docs:** when Milestones **7–10** are complete, mark them **(done)** here and refresh the **Model note** / **Baseline** to describe the **final** split (**heap `Scheduler`**, **`BrowserSchedulerHarness`**, **`UnstableMockScheduler`**, fork harnesses) in a few sentences.

---

## “100% parity” definitions (two levels)

**A. Current repo gate (today)**  
Every row you already track in **`tests_upstream/MANIFEST.json`** for **`schedulyr`** / scheduler integration is **`implemented`** and passing (heap **`Scheduler`**, **`SchedulerBrowser`**, **`SchedulerMock`**, plus **`react_dom.createRoot.schedulerIntegration`** where listed).

**B. Full upstream `__tests__` parity (Milestones 4–10)**  
Every test file under [`packages/scheduler/src/__tests__`](https://github.com/facebook/react/tree/main/packages/scheduler/src/__tests__) is covered per Milestone 10, with **`schedulyr`** (and host mocks) sufficient to run the translated suite with no missing cases except documented **non-goals**.

---

## Non-goals (unless the manifest changes)

- **Wall-clock** timing guarantees — semantics remain relative to injected **`now`** and deterministic host mocks (**`FakeTimers`** or the Milestone 5 harness clock), not real OS scheduling jitter.
- **Real browser or Node** execution of upstream **`scheduler`** package — upstream remains the **semantic** reference; the port is validated via translated tests.

**Note:** **Milestone 5** adds **`MockBrowserRuntime`** (**`Post Message` / `Message Event`**) for **`SchedulerBrowser`** parity. **Milestone 6** adds **`UnstableMockScheduler`** for **`unstable_mock`** / virtual-time parity. The default **`Scheduler`** API remains heap-only for embedders that do not need those surfaces.
