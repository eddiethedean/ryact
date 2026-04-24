# schedulyr

[![PyPI](https://img.shields.io/pypi/v/schedulyr.svg)](https://pypi.org/project/schedulyr/)
[![Python](https://img.shields.io/pypi/pyversions/schedulyr.svg)](https://pypi.org/project/schedulyr/)
[![CI](https://github.com/eddiethedean/ryact/actions/workflows/ci.yml/badge.svg)](https://github.com/eddiethedean/ryact/actions/workflows/ci.yml)

**schedulyr** is a Python port of [React Scheduler](https://github.com/facebook/react/tree/main/packages/scheduler): cooperative priorities, delayed work, continuations, and host-specific scheduling slices that upstream Jest tests assert against.

In the **ryact** monorepo, translated tests live under [`tests_upstream/scheduler/`](../../tests_upstream/scheduler/) and import **`schedulyr`** directly. **`ryact`** re-exports **`schedulyr`**'s default **`Scheduler`** as **`ryact.scheduler`** for app code; parity harnesses (**browser**, **mock**, **fork**) stay in this package—see [`SCHEDULER_ENTRYPOINTS.md`](SCHEDULER_ENTRYPOINTS.md).

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

## User guides

If you’re using `schedulyr` directly (not working on parity), start here:

- [`docs/README.md`](docs/README.md)
- [`docs/core_scheduler.md`](docs/core_scheduler.md)
- [`docs/production_scheduler.md`](docs/production_scheduler.md)
- [`docs/host_harnesses.md`](docs/host_harnesses.md)
- [`docs/cross_runtime_suite.md`](docs/cross_runtime_suite.md)

---

## Core semantics (`Scheduler`)

- **`schedule_callback(priority, fn, delay_ms=0)`** — returns a task **`id`**; **`delay_ms < 0`** is clamped to **0**; delayed work uses a **timer queue** until **`now() + delay_ms/1000`**, then a **task queue** ordered by **expiration** (priority timeout table, same numbers as **`UnstableMockScheduler`** / React **`Scheduler.js`**).
- **`cancel_callback(task_id)`** — lazy cancel: the task is skipped when popped.
- **Continuations** — if a callback **returns** another **0-arg** callable, it is queued with the same priority and **expiration from `now()`** after the callback (return **`None`** when finished).
- **`run_until_idle(time_slice_ms=None, *, max_tasks=None)`** — advances timers and drains ready work; **`time_slice_ms`** caps wall time checked before each task and after each callback; optional **`max_tasks`** caps how many callbacks run per call (Milestone **15** cooperative chunking); **`time_slice_ms=0`** or **`max_tasks=0`** can yield without running work until **`now`** or a later drain.
- **Re-entrancy** — **`schedule_callback`** may be called from inside a running task; the queues stay consistent.
- **Errors** — if a task raises, the exception propagates out of **`run_until_idle`**; remaining work stays queued for a later drain (React-style “log and continue” is not implemented unless parity tests require it).

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

The default **`Scheduler`** uses **timer** and **task** heaps (Milestone **14**); browser / mock / fork harnesses cover host integration for translated tests. **`ryact`** uses this **`Scheduler`** in the reconciler—see [`ROADMAP.md`](ROADMAP.md) and [`SCHEDULER_ENTRYPOINTS.md`](SCHEDULER_ENTRYPOINTS.md).

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

## Optional validation (Milestone 17)

These tools are **not** part of the default CI gate. They are intended as optional confidence layers.

### Node/Jest smoke + Python scenario record/compare

Record Python scenario logs:

```bash
.venv/bin/python scripts/scheduler_node_crosscheck.py python-record --out artifacts/scheduler_crosscheck.json
```

Compare against a previously recorded file:

```bash
.venv/bin/python scripts/scheduler_node_crosscheck.py python-compare --out artifacts/scheduler_crosscheck.json
```

### Curated cross-runtime production suite (Milestone 23)

This is an **optional** local workflow that records the same curated scheduler scenarios from:

- **Python** (this repo’s harnesses)
- **Upstream** `facebook/react` (requires a local checkout + dependencies installed)

Then compares the per-scenario event logs.

Record Python scenarios:

```bash
.venv/bin/python scripts/scheduler_node_crosscheck.py python-record --out artifacts/scheduler_crosscheck_python.json
```

Record upstream scenarios:

```bash
.venv/bin/python scripts/scheduler_node_crosscheck.py upstream-record --react-path /path/to/react --out artifacts/scheduler_crosscheck_upstream.json
```

Cross-compare:

```bash
.venv/bin/python scripts/scheduler_node_crosscheck.py cross-compare --python-json artifacts/scheduler_crosscheck_python.json --upstream-json artifacts/scheduler_crosscheck_upstream.json
```

Notes:

- The upstream recorder uses React’s Jest transformer (`scripts/jest/preprocessor.js`) under the hood, so the upstream checkout must have dependencies installed (e.g. `yarn install`).
- This suite is designed to be **deterministic**: it uses mock hosts and virtual clocks; avoid wall-clock timing in scenarios.

Optional upstream Jest smoke (requires a local `facebook/react` checkout + node tooling):

```bash
.venv/bin/python scripts/scheduler_node_crosscheck.py jest-smoke --react-path /path/to/react
```

---

## Production parity D checklist (Milestones 18–23)

This is the repo’s **“every runtime/host detail”** target described in [`ROADMAP.md`](ROADMAP.md) (Parity **D**).

- **DOM export surface (M18)**: `src/schedulyr/production_scheduler.py` + `tests_upstream/scheduler/test_scheduler_production_api_surface.py` (`MANIFEST` id `scheduler.productionApiSurface`)
- **DOM host loop semantics (M19)**: `src/schedulyr/production_dom_scheduler.py` + `tests_upstream/scheduler/test_scheduler_production_host_loop.py` (`MANIFEST` id `scheduler.productionHostLoop`) + `tests_upstream/scheduler/SCHEDULER_PRODUCTION_HOST_CONTRACT.md`
- **Production profiling (M20)**: `src/schedulyr/production_scheduler.py` + `tests_upstream/scheduler/test_scheduler_production_profiling.py` (`MANIFEST` id `scheduler.productionProfiling`) + `tests_upstream/scheduler/SCHEDULER_PRODUCTION_PROFILING_CONTRACT.md`
- **Native fork surface (M21)**: `src/schedulyr/native_scheduler.py` + `tests_upstream/scheduler/test_scheduler_native_api_surface.py` (`MANIFEST` id `scheduler.native.SchedulerNativeApiSurface`)
- **postTask consolidation (M22)**: `src/schedulyr/post_task_scheduler.py` + `tests_upstream/scheduler/test_scheduler_posttask_production_semantics.py` (`MANIFEST` id `scheduler.fork.SchedulerPostTaskProductionSemantics`)
- **Curated cross-runtime suite (M23)**:
  - Python scenarios: `tests_upstream/scheduler/node_crosscheck_scenarios.py`
  - Upstream recorder: `scripts/scheduler_upstream_record.cjs`
  - Runner/compare: `scripts/scheduler_node_crosscheck.py upstream-record` and `cross-compare`

## Upstream drift playbook (targeting `facebook/react` `main`)

When upstream adds/changes scheduler tests or semantics, keep parity D green by:

- **Inventory drift check** (requires a local `facebook/react` checkout):

```bash
.venv/bin/python scripts/check_scheduler_upstream_inventory.py /path/to/react
```

- **Regenerate inventory** after upstream changes:

```bash
.venv/bin/python scripts/update_scheduler_upstream_inventory.py /path/to/react
```

- **Triage** new `pending` rows in `tests_upstream/scheduler/upstream_inventory.json`:
  - port the behavior + add/extend pytest translations
  - or mark as `non_goal` with rationale
- **Keep `tests_upstream/MANIFEST.json` consistent**: any new scheduler gate row must be backed by at least one inventory case (schema tests enforce this).
- **Re-run**:
  - `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest tests_upstream/scheduler/`
  - optional: record + cross-compare scenarios (M23 workflow above)

CI already runs the drift check against a shallow upstream clone; this playbook is for local iteration and quick fixes.
### Benchmarks (pyperf)

```bash
python -m pip install pyperf
python benchmarks/run_scheduler_bench.py --n 20000 -o bench.json
python -m pyperf stats bench.json
```

### Property tests (Hypothesis)

```bash
python -m pip install hypothesis
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest tests_property/
```

---

## Further reading

- [`ROADMAP.md`](ROADMAP.md) — milestones, manifest table, inventory policy
- [`SCHEDULER_ENTRYPOINTS.md`](SCHEDULER_ENTRYPOINTS.md) — Python modules vs upstream files and **`ryact`** usage
- [Root `README.md`](../../README.md) — workspace setup, **`ty`**, **ruff**, full **`pytest`**

**Upstream source tree:** `https://github.com/facebook/react/tree/main/packages/scheduler`
