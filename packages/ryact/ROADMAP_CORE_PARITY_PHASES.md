# ryact core parity roadmap: big features (phases)

This roadmap outlines major feature areas that currently have a large number of upstream
`tests_upstream/react/upstream_inventory.json` items marked `non_goal`, and represents a
conceptual path to bring these areas into scope for `ryact` core parity.

Each phase is tied to upstream test buckets and harness dependencies. Completing a phase
should make a meaningful chunk of previously `non_goal` inventory items eligible to flip to
`pending` (or directly to `implemented` via manifest-gated translated slices).

## Phase 1: Richer Noop Renderer Harness

**Goal**: Enhance `ryact-testkit`’s noop renderer harness so Suspense + Hooks tests can
deterministically drive partial work, scheduled work, and time-dependent behavior.

**Currently non_goal buckets unlocked**:
- `packages/react-reconciler/src/__tests__/ReactSuspenseWithNoopRenderer-test.js`
- `packages/react-reconciler/src/__tests__/ReactHooksWithNoopRenderer-test.js`

**Key capabilities**:
- **Deterministic partial flush + waitFor-style helpers**: Provide a stable test API for
  “flush N steps/yields” and “flush until predicate becomes true”.
- **Scheduler-backed roots convenience**: Offer helpers that run scheduled flushes for
  `create_noop_root(scheduler=...)` roots (tests should not have to manually reach into
  reconciler internals).
- **Time control**: Provide a supported `FakeTimers` + scheduler wiring so tests can
  advance time and flush scheduled work predictably.
- **Cache surfaces (future sub-slice)**: Add `unstable_getCacheForType`-style helpers and
  `readText`-like resources to model common Suspense/noop patterns used upstream.
- **Passive effect sequencing (future sub-slice)**: Refine passive effect ordering and
  error propagation from passive teardowns as required by the upstream buckets.

**Exit criteria**:
- A growing set of manifest-gated translated tests for `ReactSuspenseWithNoopRenderer` and
  `ReactHooksWithNoopRenderer` that previously depended on missing harness primitives.
- Inventory items in those buckets can be re-classified from `non_goal` to `implemented`
  as the harness dependency is removed (or to `pending` for later incremental slices).

## Phase 2: Concurrent Work Loop (Interruption, Resume, Deprioritization)

**Goal**: Implement core concurrent reconciler behavior for time-slicing, interruption,
and resuming work at different priorities.

**Buckets unlocked**:
- `packages/react-reconciler/src/__tests__/ReactIncremental-test.js`
- `packages/react-reconciler/src/__tests__/ReactIncrementalUpdates-test.js`
- Parts of `ReactIncrementalErrorHandling-test.internal.js`
- Parts of `ReactIncrementalSideEffects-test.js`

**Exit criteria**:
- Deterministic, test-driven preemption/yield/resume in translated slices.

## Phase 3: Experimental `use()` Hook + Thenable/Cache Coordination

**Goal**: Implement the experimental `use()` API and integrate it with thenables and cache
surfaces.

**Buckets unlocked**:
- `packages/react-reconciler/src/__tests__/ReactUse-test.js`

## Phase 4: SuspenseList & Advanced Suspense Reveal Ordering

**Goal**: Implement `SuspenseList` and advanced Suspense reveal ordering semantics.

**Buckets unlocked**:
- `packages/react-reconciler/src/__tests__/ReactSuspenseList-test.js`
- Remaining `ReactSuspense-test.internal.js` and `ReactSuspenseEffectsSemantics-test.js`

## Phase 5: “Real” Lazy Semantics & Code Splitting

**Goal**: Expand `lazy()` beyond synchronous resolution to match upstream behavior
including async loading, error propagation, and Suspense integration.

**Buckets unlocked**:
- `packages/react-reconciler/src/__tests__/ReactLazy-test.internal.js`

## Phase 6: Profiler & Scheduler Instrumentation

**Goal**: Implement profiling/tracing hooks and scheduler instrumentation needed for
profiler and transition tracing suites.

**Buckets unlocked**:
- `packages/react/src/__tests__/ReactProfiler-test.internal.js`
- `packages/react-reconciler/src/__tests__/ReactTransitionTracing-test.js`
- `packages/react/src/__tests__/ReactProfilerDevToolsIntegration-test.internal.js`

