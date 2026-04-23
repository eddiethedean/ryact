# schedulyr roadmap

Parity target: **React Scheduler** — `facebook/react` `packages/scheduler` (priorities, delayed work, cooperative execution, and whatever upstream tests assert).

Work is gated by **`tests_upstream/MANIFEST.json`**: scheduler-related rows must stay green in CI. Translated scheduler tests live under **`tests_upstream/scheduler/`** (e.g. **`test_deterministic_fake_time.py`** for manifest id **`scheduler.deterministicFakeTime`**). Imports should target **`schedulyr`** directly so the suite exercises this package, not only the **`ryact.scheduler`** re-export.

**Consumers:** **`ryact`** re-exports this module as **`ryact.scheduler`** for convenience; **`ryact-testkit.FakeTimers`** supplies deterministic **`now`** for tests.

---

## Baseline today (implemented sketch)

- **Priority constants** — `IMMEDIATE_PRIORITY` … `IDLE_PRIORITY` (numeric ordering; lower value = runs before higher value when **due times are equal**).
- **`Scheduler`** — injectable **`now`** (defaults to **`time.monotonic`**); min-heap of **`(due, priority, task_id, callback)`**.
- **`schedule_callback(priority, callback, delay_ms=0)`** — returns an opaque task id; **`due = now() + delay_ms/1000`**.
- **`run_until_idle(time_slice_ms=None)`** — drains **due** work in heap order:
  - If the earliest task is **not yet due**, it is pushed back and the run **returns** (no busy-wait; time must advance via **`now`** or **`FakeTimers`**).
  - Optional **`time_slice_ms`** sets a **deadline** on **`now`**; when exceeded, returns with work possibly still queued.
- **`default_scheduler`** — module-level instance (use sparingly in tests; prefer explicit **`Scheduler()`**).

Not implemented yet (placeholders for later milestones): cancellation, continuation / “more work” callbacks, starvation guarantees, message-channel / browser-specific assumptions, and full alignment with React’s **frame** / **idle** plumbing.

---

## Milestone 0 — Harness + manifest alignment **(done)**

- **`tests_upstream/scheduler/`** exists; the delayed-work smoke test uses **`FakeTimers`** + **`schedulyr.Scheduler`** (no **`sleep`**).
- **`MANIFEST.json`** maps **`scheduler.deterministicFakeTime`** → **`tests_upstream/scheduler/test_deterministic_fake_time.py`**.

**When you add more scheduler parity:** put new **`test_*.py`** files under **`tests_upstream/scheduler/`**, add a manifest row per file (or per tracked upstream slice), and keep using **`FakeTimers`** (or another injected **`now`**) for time. Note: upstream **`Scheduler-test.js`** is largely **`SchedulerBrowser`** + **`MessageChannel`** mocks; many cases will need a Python mock runtime or API growth before they translate one-to-one (see non-goals).

## Milestone 1 — Core semantics

- **Ordering** — priority + due-time rules matching upstream (including ties and stability where tests care).
- **Delayed work** — `delay_ms` / due-time edge cases (rounding, ordering with priorities).
- **Cooperative yielding** — **`run_until_idle(time_slice_ms=...)`** (and any API upstream expects) so work can be **paused** and resumed across advances of **`now`**.
- **Continuations** — if upstream tests require callbacks that **reschedule** or return follow-up work, model that explicitly.
- **Cancellation** — only if / when manifest tests require it.

## Milestone 2 — Edge cases + integration

- **Re-entrancy** — scheduling from inside running callbacks without corrupting heap or ordering.
- **Fairness / starvation** — behavior upstream tests lock in (if any).
- **Profiling / tracing** — only if tests assert on hooks or ordering artifacts.

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
