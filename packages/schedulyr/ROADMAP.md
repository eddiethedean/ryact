# schedulyr roadmap

Parity target: React Scheduler (`facebook/react` `packages/scheduler`).

## Milestone 0 — Harness + reference alignment
- Translate a minimal set of upstream scheduler tests into `tests_upstream/scheduler/`.
- Ensure fake time is deterministic and drives scheduler behavior (no real `sleep`).
- Establish a parity manifest section for scheduler tests.

## Milestone 1 — Core semantics
- Priority levels and ordering guarantees.
- Delayed callbacks (`delay_ms`) and due-time handling.
- Cooperative yielding: run-to-deadline / time slicing.
- Continuations: callbacks that return more work (if required by tests).
- Cancellation APIs (if required by tests).

## Milestone 2 — Edge cases + dev tooling
- Re-entrancy and nested scheduling.
- Starvation prevention / fairness (as asserted by upstream).
- Optional profiling/tracing hooks (only if tests assert).

## “100% parity” definition
- All upstream Scheduler tests selected in `tests_upstream/MANIFEST.json` are translated and passing.
- No skipped tests without an explicit non-goal entry.

