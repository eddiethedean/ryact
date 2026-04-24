# schedulyr

[![PyPI](https://img.shields.io/pypi/v/schedulyr.svg)](https://pypi.org/project/schedulyr/)
[![Python](https://img.shields.io/pypi/pyversions/schedulyr.svg)](https://pypi.org/project/schedulyr/)
[![CI](https://github.com/eddiethedean/ryact/actions/workflows/ci.yml/badge.svg)](https://github.com/eddiethedean/ryact/actions/workflows/ci.yml)

**schedulyr** is a Python port of [React Scheduler](https://github.com/facebook/react/tree/main/packages/scheduler): cooperative priorities, delayed work, continuations, and host-specific scheduling slices that upstream Jest tests assert against.

In the **ryact** monorepo, translated tests live under [`tests_upstream/scheduler/`](../../tests_upstream/scheduler/) and import **`schedulyr`** directly. **`ryact`** re-exports the heap scheduler as **`ryact.scheduler`** for app code; parity harnesses (**browser**, **mock**, **fork**) stay in this package—see [`SCHEDULER_ENTRYPOINTS.md`](SCHEDULER_ENTRYPOINTS.md).

---

## Install

**Published package** (when you only need the library):

```bash
pip install schedulyr
```

**Monorepo development** (recommended for parity work): from the repo root, use a [`.venv`](../../README.md) and editable installs as in the root README, including **`schedulyr`**:

```bash
python -m pip install -e packages/schedulyr -e packages/ryact -e packages/ryact-dom -e packages/ryact-native -e packages/ryact-testkit
```

---

## Quick example

```python
from schedulyr import NORMAL_PRIORITY, Scheduler

s = Scheduler()
s.schedule_callback(NORMAL_PRIORITY, lambda: print("work"), delay_ms=0)
s.run_until_idle()
```

Public exports include **`Scheduler`**, priority constants, **`BrowserSchedulerHarness`** + **`MockBrowserRuntime`**, **`UnstableMockScheduler`**, fork harnesses (**`PostTask*`**, **`SetImmediate*`**, **`SetTimeout*`**), **`SchedulerBrowserFlags`**, and unstable priority aliases used by browser-style tests. See [`src/schedulyr/__init__.py`](src/schedulyr/__init__.py).

---

## Core semantics (heap `Scheduler`)

- **`schedule_callback(priority, fn, delay_ms=0)`** — returns a task **`id`**; **`delay_ms < 0`** is clamped to **0**; due time is **`now() + delay_ms/1000`**.
- **`cancel_callback(task_id)`** — lazy cancel: the task is skipped when popped.
- **Continuations** — if a callback **returns** another **0-arg** callable, it is queued with the same priority and **due** **`now()`** after the callback (return **`None`** when finished).
- **`run_until_idle(time_slice_ms=None)`** — drains due work; **`time_slice_ms`** caps wall time checked before each task and after each callback; **`time_slice_ms=0`** yields until **`now`** advances.
- **Re-entrancy** — **`schedule_callback`** may be called from inside a running task; the heap stays consistent.
- **Errors** — if a task raises, the exception propagates out of **`run_until_idle`**; remaining work stays on the heap for a later drain (React-style “log and continue” is not implemented unless parity tests require it).

---

## Upstream slices (parity harnesses)

| Area | Python surface | Upstream tests (indicative) |
|------|------------------|---------------------------|
| Browser host | **`MockBrowserRuntime`**, **`BrowserSchedulerHarness`** | **`Scheduler-test.js`** — **`describe('SchedulerBrowser')`** |
| Mock / virtual time | **`UnstableMockScheduler`** | **`SchedulerMock-test.js`** — see [`SCHEDULER_MOCK_CONTRACT.md`](../../tests_upstream/scheduler/SCHEDULER_MOCK_CONTRACT.md) |
| Profiling | **`UnstableMockScheduler(enable_profiling=True)`** | **`SchedulerProfiling-test.js`** — [`SCHEDULER_PROFILING_CONTRACT.md`](../../tests_upstream/scheduler/SCHEDULER_PROFILING_CONTRACT.md) |
| **`postTask`** | **`PostTaskSchedulerHarness`**, **`PostTaskMockRuntime`** | **`SchedulerPostTask-test.js`** — [`SCHEDULER_POSTTASK_CONTRACT.md`](../../tests_upstream/scheduler/SCHEDULER_POSTTASK_CONTRACT.md) |
| **`setImmediate`** | **`SetImmediateSchedulerHarness`**, **`SetImmediateMockRuntime`** | **`SchedulerSetImmediate-test.js`** — [`SCHEDULER_SETIMMEDIATE_CONTRACT.md`](../../tests_upstream/scheduler/SCHEDULER_SETIMMEDIATE_CONTRACT.md) |
| **`setTimeout(0)`** | **`SetTimeoutSchedulerHarness`** | **`SchedulerSetTimeout-test.js`** — [`SCHEDULER_SETTIMEOUT_CONTRACT.md`](../../tests_upstream/scheduler/SCHEDULER_SETTIMEOUT_CONTRACT.md) |

The default **`Scheduler`** is a single min-heap; React’s production fork splits timer vs task queues and host integration. **`ryact`** uses only the heap **`Scheduler`** in the reconciler; browser and fork harnesses exist for translated upstream tests—see the model note in [`ROADMAP.md`](ROADMAP.md).

---

## Parity, manifest, and inventory

- **CI manifest** — [`tests_upstream/MANIFEST.json`](../../tests_upstream/MANIFEST.json) lists implemented scheduler parity rows (e.g. **`scheduler.browser.SchedulerBrowserParity`**, **`scheduler.mock.*`**, **`scheduler.fork.*`**). Full table: [`ROADMAP.md` — *Parity slice tracked in CI*](ROADMAP.md#parity-slice-tracked-in-ci).
- **Upstream checklist** — [`tests_upstream/scheduler/upstream_inventory.json`](../../tests_upstream/scheduler/upstream_inventory.json): one row per Jest case under the six files in [`packages/scheduler/src/__tests__`](https://github.com/facebook/react/tree/main/packages/scheduler/src/__tests__). At pinned **`upstream_ref`** (**`main`**), every row is **`implemented`** (with **`manifest_id`** + **`python_test`**) or **`non_goal`** with rationale; **Milestone 13** requires **zero** **`pending`**, enforced by **`test_scheduler_inventory_has_no_pending`** in [`test_upstream_inventory_schema.py`](../../tests_upstream/scheduler/test_upstream_inventory_schema.py).
- **Regen / drift** (from repo root, with a local **`facebook/react`** clone):

  ```bash
  .venv/bin/python scripts/update_scheduler_upstream_inventory.py /path/to/react
  .venv/bin/python scripts/check_scheduler_upstream_inventory.py /path/to/react
  ```

  CI runs the drift check in **`.github/workflows/ci.yml`** (**`scheduler_upstream_drift`**).

Roadmap, milestones, **“100% parity” B** (inventory, **M13**), and **parity C** (**M14–M17**, deeper **`Scheduler.js`** / **`ryact`** alignment): [`ROADMAP.md`](ROADMAP.md).

---

## Running tests

Scheduler parity tests are not inside this package; run them from the **ryact** root:

```bash
cd /path/to/ryact
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/pytest tests_upstream/scheduler/
```

Parallel runs (**pytest-xdist**): with **`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`**, load the plugin explicitly:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/pytest tests_upstream/scheduler/ -p xdist.plugin -n auto
```

---

## Further reading

- [`ROADMAP.md`](ROADMAP.md) — milestones, manifest table, inventory policy
- [`SCHEDULER_ENTRYPOINTS.md`](SCHEDULER_ENTRYPOINTS.md) — Python modules vs upstream files and **`ryact`** usage
- [Root `README.md`](../../README.md) — workspace setup, **`ty`**, **ruff**, full **`pytest`**

**Upstream source tree:** `https://github.com/facebook/react/tree/main/packages/scheduler`
