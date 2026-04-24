# Scheduler entrypoints (Python vs upstream)

Canonical **feature flags** (React `SchedulerFeatureFlags` / Jest `gate` subset): [`src/schedulyr/scheduler_browser_flags.py`](src/schedulyr/scheduler_browser_flags.py) — `SchedulerBrowserFlags`, `gate()`.

Shared **browser-style work loop** (timer heap + task heap + `enableAlwaysYieldScheduler`): [`src/schedulyr/_browser_style_work_loop.py`](src/schedulyr/_browser_style_work_loop.py) — used by `BrowserSchedulerHarness`, `SetImmediateSchedulerHarness`, `SetTimeoutSchedulerHarness`.

| Python module | Upstream surface | Used by `ryact`? |
|---------------|------------------|------------------|
| [`scheduler.py`](src/schedulyr/scheduler.py) `Scheduler` | `Scheduler.js` timer + task heaps, expiration (M14); **`max_tasks`** cooperative cap (M15); legacy manifest rows + **`scheduler.productionWorkLoop`** + **`scheduler.fairness.cooperativeDrain`** | **Yes** — [`reconciler.py`](../ryact/src/ryact/reconciler.py) `Root(scheduler=…)`, `schedule_update_on_root`, `lane_to_scheduler_priority` |
| [`production_scheduler.py`](src/schedulyr/production_scheduler.py) | Default DOM fork `Scheduler.js` exported `unstable_*` surface (M18) + production `unstable_Profiling` (M20) | No |
| [`production_dom_scheduler.py`](src/schedulyr/production_dom_scheduler.py) | Default DOM fork `Scheduler.js` host driver selection + `performWorkUntilDeadline` yielding contract (M19) | No |
| [`native_scheduler.py`](src/schedulyr/native_scheduler.py) | Native fork `SchedulerNative.js` (runtime injection + disabled APIs throw; `unstable_Profiling` is `null`) (M21) | No |
| [`browser_scheduler.py`](src/schedulyr/browser_scheduler.py) `BrowserSchedulerHarness` | `Scheduler-test.js` `describe('SchedulerBrowser')`, MessageChannel host | No |
| [`mock_scheduler.py`](src/schedulyr/mock_scheduler.py) `UnstableMockScheduler` | `unstable_mock`, `SchedulerMock-test.js`, profiling | No |
| [`post_task_scheduler.py`](src/schedulyr/post_task_scheduler.py) | `SchedulerPostTask.js` | No |
| [`set_immediate_scheduler.py`](src/schedulyr/set_immediate_scheduler.py) | `setImmediate` host path | No |
| [`set_timeout_scheduler.py`](src/schedulyr/set_timeout_scheduler.py) | `setTimeout(0)` host path | No |

`ryact-dom` deferred flush with a passed-in scheduler is covered by **`react_dom.createRoot.schedulerIntegration`** in `tests_upstream/MANIFEST.json` ([`test_create_root_scheduler_integration.py`](../../tests_upstream/react_dom/test_create_root_scheduler_integration.py)).

Full **`__tests__`** inventory closure (**regen → heap ports → browser ports → zero `pending`**) is tracked as Milestones **10–13** in [`ROADMAP.md`](ROADMAP.md).

## Milestone 10 triage: `Scheduler-test.js` `describe_path` buckets

Use this when **[`update_scheduler_upstream_inventory.py`](../../scripts/update_scheduler_upstream_inventory.py)** adds new rows (typically **`pending`**) after upstream adds or renames Jest cases. Set optional per-row **`notes`** in [`upstream_inventory.json`](../../tests_upstream/scheduler/upstream_inventory.json) for “target harness” hints.

| `describe_path` (upstream) | Milestone | Port target |
|----------------------------|------------|----------------|
| **`SchedulerBrowser`** | **M12** (browser slice) | [`MockBrowserRuntime`](src/schedulyr/mock_browser_runtime.py) + [`BrowserSchedulerHarness`](src/schedulyr/browser_scheduler.py); manifest **`scheduler.browser.*`** |
| *(future top-level describes)* using **only** cooperative heap + `schedule_callback` / `run_until_idle` semantics | **M11** (heap) | [`FakeTimers`](../../packages/ryact-testkit/src/ryact_testkit/fake_timers.py) + [`Scheduler`](src/schedulyr/scheduler.py); manifest first five **`scheduler.*`** heap rows or new split ids |
| *(future)* **`gate`**, DOM-only, or Jest environment noise | **M12** or **M13** | **M12** if browser/runtime extension is justified; **M13** **`non_goal`** with **`non_goal_rationale`** if not worth porting |

**Current upstream (`facebook/react` `main`, shallow clone):** [`Scheduler-test.js`](https://github.com/facebook/react/blob/main/packages/scheduler/src/__tests__/Scheduler-test.js) contains only **`describe('SchedulerBrowser')`** (**9** `it` blocks). Those rows are **`implemented`** in inventory; heap overlap is already cross-linked in row **`notes`** to **`tests_upstream/scheduler/test_*.py`** manifest rows.

**Milestone 11:** At this pin there are **no** **`pending`** rows under **`Scheduler-test.js`**, so there is **no** heap-triaged backlog to port. **M11** is **(done)** until regen adds **`pending`** rows whose **`describe_path`** is triaged to **M11 heap** (see table above); then follow **When this fires again** in [`ROADMAP.md`](ROADMAP.md) under Milestone **11**.

**Milestone 12:** All **`SchedulerBrowser`** inventory rows are **`implemented`** (**`scheduler.browser.SchedulerBrowserParity`**); there is **no** browser-triaged **`pending`** backlog at this pin. **M12** is **(done)** until regen adds **`pending`** rows triaged to **M12** (e.g. new **`SchedulerBrowser`** `it` blocks or other browser-harness suites); then follow **When this fires again** in [`ROADMAP.md`](ROADMAP.md) under Milestone **12** and update [`SCHEDULER_BROWSER_CONTRACT.md`](../../tests_upstream/scheduler/SCHEDULER_BROWSER_CONTRACT.md) if **`assertLog`** sequences change.

**Milestone 13:** All six scheduler **`__tests__`** files are fully represented in inventory with **no** **`pending`** rows at **`upstream_ref`:** **`main`** (**pytest** **`test_scheduler_inventory_has_no_pending`** in [`test_upstream_inventory_schema.py`](../../tests_upstream/scheduler/test_upstream_inventory_schema.py)). **M13** is **(done)**; if regen reintroduces **`pending`**, clear them before merge (see **When this regresses** under M13 in [`ROADMAP.md`](ROADMAP.md)).

**Drift / regen:** CI runs [`check_scheduler_upstream_inventory.py`](../../scripts/check_scheduler_upstream_inventory.py) against **`main`** (see [`.github/workflows/ci.yml`](../../.github/workflows/ci.yml)). Pin in inventory: **`upstream_ref`** = **`main`** (see JSON header).

## Milestone 14 — `Scheduler.js` work-loop parity matrix (first slice)

**Decision:** **`Scheduler`** was refactored **in place** (no `ProductionScheduler` class). Public API is unchanged: **`schedule_callback`**, **`cancel_callback`**, **`run_until_idle`**, priority constants. **`ryact`** continues to import **`schedulyr.Scheduler`** with no code changes.

| React `Scheduler.js` concept | Python location | Observable in this slice? | Tests |
|------------------------------|-----------------|----------------------------|-------|
| `timerQueue` min-heap (`sortIndex` = `startTime`) | [`scheduler.py`](src/schedulyr/scheduler.py) `_timer_heap` entries ordered by `start_time` | Yes — delayed work waits until `start_time` | Legacy delay tests + [`test_scheduler_production_work_loop.py`](../../tests_upstream/scheduler/test_scheduler_production_work_loop.py) |
| `advanceTimers` → promote to `taskQueue` | `_advance_timers()` | Yes | Same |
| `taskQueue` order by `expirationTime` then `id` | `_task_heap` `(expiration_time, id, _Task)` | Yes — matches prior `(due, priority, id)` ordering for the public API | All heap manifest modules + **`scheduler.productionWorkLoop`** |
| Priority timeout → `expirationTime` | `_expiration_offset_seconds()` (ms → s, same numbers as [`mock_scheduler.py`](src/schedulyr/mock_scheduler.py)) | Yes (indirect) | Production work-loop tests |
| `unstable_scheduleCallback` continuation yields host; Python runs continuations synchronously | New continuation `_Task` pushed to `_task_heap` after callback | Preserved — same as pre-M14 heap behavior | [`test_cancel_continuation.py`](../../tests_upstream/scheduler/test_cancel_continuation.py), [`test_reentrancy_and_errors.py`](../../tests_upstream/scheduler/test_reentrancy_and_errors.py) |
| `shouldYieldToHost` / `frameYieldMs` / `enableAlwaysYieldScheduler` | Not in `scheduler.py` | No — still host/browser concerns; **`time_slice_ms`** remains the embedder yield knob | [`test_delay_time_slice.py`](../../tests_upstream/scheduler/test_delay_time_slice.py) |

**Not extracted to a shared module:** `_advance_timers` stays local to [`scheduler.py`](src/schedulyr/scheduler.py); [`_browser_style_work_loop.py`](src/schedulyr/_browser_style_work_loop.py) already covers browser-shaped drivers with a different task type. Revisit if a third copy appears.

**Further Parity C work (M14 follow-ups or M15+):** frame-aligned **`shouldYield`**, starvation between equal-expiration bands, **`needsPaint`** — only when **`MANIFEST`** / inventory-backed tests require them.

## Milestone 15 — Cooperative drain (first slice)

| Behavior | Python | Tests / contract |
|----------|--------|-------------------|
| Optional **`max_tasks`** per **`run_until_idle`** | [`scheduler.py`](src/schedulyr/scheduler.py) | [`test_scheduler_fairness.py`](../../tests_upstream/scheduler/test_scheduler_fairness.py), [`SCHEDULER_FAIRNESS_CONTRACT.md`](../../tests_upstream/scheduler/SCHEDULER_FAIRNESS_CONTRACT.md), **`MANIFEST`** **`scheduler.fairness.cooperativeDrain`** |

**`ryact`:** unchanged — reconciler does not pass **`max_tasks`**; default drain semantics stay the same.
