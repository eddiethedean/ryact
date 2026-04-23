# ryact roadmap

Parity target: React core (`facebook/react` `packages/react`).

## Milestone 0 — Test translation pipeline
- Translate a smoke slice of `packages/react/src/__tests__` into `tests_upstream/react/`.
- Standardize helpers in `ryact-testkit` (warnings, act, fake timers, renderer helpers).
- Keep `tests_upstream/MANIFEST.json` as the parity gate (CI enforced).

## Milestone 1 — Elements + component model
- Element identity rules, key/ref handling, children normalization.
- Function component rendering rules + basic update semantics.
- Dev warnings that upstream tests assert on.
- Basic context semantics and propagation.

## Milestone 2 — Hooks parity (incremental)
- Enforce rules-of-hooks and invalid usage warnings.
- `useState`/`useReducer` behavior under re-rendering and batching.
- Effect semantics:
  - passive vs layout ordering
  - cleanup ordering
  - strict-mode behaviors when asserted
- Add remaining hooks as demanded by translated tests (`useContext`, etc.).

## Milestone 3 — Reconciler (“Fiber-like”) correctness
- Stable identity model (move hook state off global maps into a proper tree/fiber identity).
- Update queues + lanes; priority propagation.
- Render/commit separation and effect lists.
- Integrate with `schedulyr` for priority + yielding behavior.

## Milestone 4 — Concurrency + Suspense (as tests demand)
- Transitions and interruption/resume.
- Suspense semantics and fallback timing/reveal ordering.

## “100% parity” definition
- All upstream React tests selected in `tests_upstream/MANIFEST.json` are translated and passing.
- API/documented deviations are explicit and tracked as non-goals (if any).

