# schedulyr roadmap

Parity target: **React Scheduler** — `facebook/react` `packages/scheduler` (priorities, delayed work, cooperative execution, and whatever upstream tests assert).

Work is gated by **`tests_upstream/MANIFEST.json`**: scheduler-related rows must stay green in CI. Translated tests live under **`tests_upstream/scheduler/`**; import **`schedulyr`** directly so the suite exercises this package, not only the **`ryact.scheduler`** re-export.

**Consumers:** **`ryact`** re-exports this module as **`ryact.scheduler`** for convenience; **`ryact-testkit.FakeTimers`** supplies deterministic **`now`** for tests.

**Model note:** this port still uses a **single** min-heap for all work. React’s implementation splits **timer** vs **task** queues, **expiration** times per priority, and host scheduling (`MessageChannel`, etc.). Those differences are intentional simplifications until translated tests force a richer shape.

---

## Baseline today (implemented sketch)

- **Priority constants** — `IMMEDIATE_PRIORITY` … `IDLE_PRIORITY` (numeric ordering; lower value = runs before higher value when **due times are equal**).
- **`Scheduler`** — injectable **`now`** (defaults to **`time.monotonic`**); min-heap of **`(due, priority, task_id, callback)`** (see [src/schedulyr/scheduler.py](src/schedulyr/scheduler.py)).
- **`schedule_callback`** — returns task **`id`**; callbacks are **`Callable[[], Any]`** (return **`None`** or a **0-arg** continuation callable); **`delay_ms < 0`** is clamped to **`0`**; **`due = now() + delay_ms/1000`**.
- **`cancel_callback(task_id)`** — lazy cancellation (skipped when the task is popped).
- **Continuations** — if a callback **returns** a callable, it is queued as new work (same **priority**, **due** = **`now()`** after the callback).
- **`run_until_idle(time_slice_ms=None)`** — drains **due** work; stops if the next head is not yet due; **`time_slice_ms`** sets a deadline checked **before each task and after each callback**. **`time_slice_ms=0`** means deadline equals **`now()`** at entry, so **no** tasks run until **`now`** moves.
- **`default_scheduler`** — module-level instance (use sparingly in tests; prefer explicit **`Scheduler()`**).

Not implemented yet (later milestones): separate **timer vs ready** queues, **expiration**-based ordering, starvation / fairness guarantees, **`shouldYield`-style** host hooks, message-channel / **rAF** / **IdleCallback** emulation.

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

Upstream path for all five rows today: **`packages/scheduler/src/__tests__/Scheduler-test.js`**.

---

## Milestone 0 — Harness + manifest alignment **(done)**

- **`tests_upstream/scheduler/`** layout; **`FakeTimers`** + **`schedulyr.Scheduler`** (no **`sleep`**).
- Manifest rows per **`python_test`** file (see table above).

**When you add more parity:** new **`test_*.py`** under **`tests_upstream/scheduler/`**, new **`MANIFEST.json`** row, same fake-time discipline. Upstream **`Scheduler-test.js`** is largely **`SchedulerBrowser`** + **`MessageChannel`** mocks; many cases need a Python mock runtime or API growth before they translate one-to-one (see non-goals).

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

## Milestone 3 — Wire to `ryact` (as reconciler matures)

- **`ryact`**’s reconciler should eventually **drive** host work through this scheduler (priorities, lanes, yields) instead of ad hoc flush paths — see **`packages/ryact/ROADMAP.md`** milestone 3–4.
- Until then, **`schedulyr`** remains independently testable; **`ryact`** keeps the thin re-export.

---

## “100% parity” definition (for this package)

- Every **Scheduler**-related test you track in **`tests_upstream/MANIFEST.json`** is translated and passing against **`schedulyr`**.
- No silently skipped assertions — if something is out of scope, record it as an explicit **non-goal** (manifest or docs).

## Non-goals (unless the manifest changes)

- Emulating **browser `postMessage` / `MessageChannel`** or real **requestAnimationFrame** / **IdleCallback** unless you add a host adapter for that environment.
- **Wall-clock** timing guarantees — semantics are defined relative to the injected **`now`** and test harness time.
