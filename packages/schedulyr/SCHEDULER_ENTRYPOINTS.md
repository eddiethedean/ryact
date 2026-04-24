# Scheduler entrypoints (Python vs upstream)

Canonical **feature flags** (React `SchedulerFeatureFlags` / Jest `gate` subset): [`src/schedulyr/scheduler_browser_flags.py`](src/schedulyr/scheduler_browser_flags.py) — `SchedulerBrowserFlags`, `gate()`.

Shared **browser-style work loop** (timer heap + task heap + `enableAlwaysYieldScheduler`): [`src/schedulyr/_browser_style_work_loop.py`](src/schedulyr/_browser_style_work_loop.py) — used by `BrowserSchedulerHarness`, `SetImmediateSchedulerHarness`, `SetTimeoutSchedulerHarness`.

| Python module | Upstream surface | Used by `ryact`? |
|---------------|------------------|------------------|
| [`scheduler.py`](src/schedulyr/scheduler.py) `Scheduler` | `Scheduler.js` core heap semantics (translated heap tests) | **Yes** — [`reconciler.py`](../ryact/src/ryact/reconciler.py) `Root(scheduler=…)`, `schedule_update_on_root`, `lane_to_scheduler_priority` |
| [`browser_scheduler.py`](src/schedulyr/browser_scheduler.py) `BrowserSchedulerHarness` | `Scheduler-test.js` `describe('SchedulerBrowser')`, MessageChannel host | No |
| [`mock_scheduler.py`](src/schedulyr/mock_scheduler.py) `UnstableMockScheduler` | `unstable_mock`, `SchedulerMock-test.js`, profiling | No |
| [`post_task_scheduler.py`](src/schedulyr/post_task_scheduler.py) | `SchedulerPostTask.js` | No |
| [`set_immediate_scheduler.py`](src/schedulyr/set_immediate_scheduler.py) | `setImmediate` host path | No |
| [`set_timeout_scheduler.py`](src/schedulyr/set_timeout_scheduler.py) | `setTimeout(0)` host path | No |

`ryact-dom` deferred flush with a passed-in scheduler is covered by **`react_dom.createRoot.schedulerIntegration`** in `tests_upstream/MANIFEST.json` ([`test_create_root_scheduler_integration.py`](../../tests_upstream/react_dom/test_create_root_scheduler_integration.py)).

Full **`__tests__`** inventory closure (**regen → heap ports → browser ports → zero `pending`**) is tracked as Milestones **10–13** in [`ROADMAP.md`](ROADMAP.md).
