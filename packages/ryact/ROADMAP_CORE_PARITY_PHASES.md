# ryact core parity roadmap: big features (phases)

This roadmap outlines major feature areas that currently have a large number of upstream
`tests_upstream/react/upstream_inventory.json` items marked `non_goal`, and represents a
conceptual path to bring these areas into scope for `ryact` core parity.

Each phase is tied to upstream test buckets and harness dependencies. Completing a phase
should make a meaningful chunk of previously `non_goal` inventory items eligible to flip to
`pending` (or directly to `implemented` via manifest-gated translated slices).

## How to use this roadmap

- **Goal of a phase**: Implement the missing runtime + test harness surface so a set of upstream
  suites can be flipped from `non_goal` to **`pending`** (pending-first), then burned down into
  manifest-gated translated slices.
- **Definition of “eligible to reopen”**: Once the phase exit criteria are met, we should add a
  dedicated inventory “reopen” wave that flips the associated non-goals back to `pending`.
- **Explicit permanent non-goals**: Some upstream suites are JS-ecosystem-specific and should
  remain out of scope (see the end of this doc).

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

## Phase 3: Lanes, Expiration, and Transition Indicators

**Goal**: Implement lane expiration/time heuristics and the scheduling signals that upstream
uses to test “expired” work, transition indicators, and retry-at-lower-priority behaviors.

**Buckets unlocked**:
- `packages/react-reconciler/src/__tests__/ReactExpiration-test.js`
- `packages/react-reconciler/src/__tests__/ReactDefaultTransitionIndicator-test.js`
- Remaining non-goals in `packages/react-reconciler/src/__tests__/ReactIncremental-test.js`
- Parts of concurrent error recovery (`ReactConcurrentErrorRecovery-test.js`)

**Key capabilities**:
- **Expiration model**: a deterministic clock source + “this lane is expired” semantics.
- **Retry semantics**: targeted “retry at lower priority” and reprioritization in the scheduler.
- **Indicator plumbing**: transition pending indicator behavior in the reconciler/harness.

## Phase 4: Suspense Ping/Retry Scheduling (Thenables → Wake → Correct Lane)

**Goal**: Make Suspense boundaries reliably suspend and *replay* work when their thenables
resolve, including integration with the noop harness and act warnings.

**Buckets unlocked**:
- `packages/react-reconciler/src/__tests__/ReactSuspenseWithNoopRenderer-test.js` (large bucket)
- Remaining internal Suspense suites that depend on ping/retry wiring

**Key capabilities**:
- **Ping list / wake queues**: track thenables per boundary and schedule the right root work.
- **Replay safety**: prevent double-commits and warning duplication on replay.
- **Harness helpers**: deterministic `waitFor...`-style helpers for “resolve thenable → flush”.

## Phase 5: Experimental `use()` Hook + Thenable/Cache Coordination

**Goal**: Implement the experimental `use()` API and integrate it with thenables and cache
surfaces.

**Buckets unlocked**:
- `packages/react-reconciler/src/__tests__/ReactUse-test.js`

## Phase 6: SuspenseList & Advanced Suspense Reveal Ordering

**Goal**: Implement `SuspenseList` and advanced Suspense reveal ordering semantics.

**Buckets unlocked**:
- `packages/react-reconciler/src/__tests__/ReactSuspenseList-test.js`
- Remaining `ReactSuspense-test.internal.js` and `ReactSuspenseEffectsSemantics-test.js`

## Phase 7: “Real” Lazy Semantics & Code Splitting

**Goal**: Expand `lazy()` beyond synchronous resolution to match upstream behavior
including async loading, error propagation, and Suspense integration.

**Buckets unlocked**:
- `packages/react-reconciler/src/__tests__/ReactLazy-test.internal.js`

## Phase 8: Profiler & Scheduler Instrumentation

**Goal**: Implement profiling/tracing hooks and scheduler instrumentation needed for
profiler and transition tracing suites.

**Buckets unlocked**:
- `packages/react/src/__tests__/ReactProfiler-test.internal.js`
- `packages/react-reconciler/src/__tests__/ReactTransitionTracing-test.js`
- `packages/react/src/__tests__/ReactProfilerDevToolsIntegration-test.internal.js`

## Phase 9: New Context + Propagation/Bailout Parity

**Goal**: Implement a more complete New Context model: provider/consumer propagation,
subscription/bailout behavior, and stable semantics across interruption/retry.

**Buckets unlocked**:
- `packages/react-reconciler/src/__tests__/ReactNewContext-test.js`
- `packages/react-reconciler/src/__tests__/ReactContextPropagation-test.js`

**Key capabilities**:
- **Propagation graph**: track which fibers read which contexts during render.
- **Bailouts**: avoid re-rendering subtrees when context values are referentially equal (or
  when selectors/observed bits indicate no relevant change).
- **Retry safety**: ensure context stacks reset correctly on yield/restart.

## Phase 10: flushSync, Batching, and Priority Shifts

**Goal**: Implement host/testkit `flushSync` and the associated batching and priority shifting
semantics needed by upstream.

**Buckets unlocked**:
- `packages/react-reconciler/src/__tests__/ReactFlushSync-test.js`
- Follow-on slices in transition/scheduling suites that assume flushSync behavior

**Key capabilities**:
- **Synchronous flush boundary**: force immediate work/commit for updates inside flushSync.
- **Batching contracts**: match upstream behavior for nested batching and priority.
- **Interop with act**: avoid false-positive act warnings for sync flushes.

## Phase 11: Offscreen / Sibling Prerendering

**Goal**: Add Offscreen-like “hidden work” and sibling prerender semantics used by upstream to
test progressive reveal and background work scheduling.

**Buckets unlocked**:
- `packages/react-reconciler/src/__tests__/ReactSiblingPrerendering-test.js`
- (Often also affects) `ReactSuspense-test.internal.js` and reveal-order timing assertions

## Phase 12: Scope API Surface (Experimental)

**Goal**: Implement the experimental Scope API surface required for internal suites.

**Buckets unlocked**:
- `packages/react-reconciler/src/__tests__/ReactScope-test.internal.js`

## Phase 13: useEffectEvent (Experimental)

**Goal**: Implement `useEffectEvent` and its nuanced interaction with effects + identity.

**Buckets unlocked**:
- `packages/react-reconciler/src/__tests__/useEffectEvent-test.js`

## Phase 14: Fragment Identity / Array Child Reconciliation

**Goal**: Implement deeper fragment identity/state preservation semantics, especially where
arrays/iterables interact with reconciliation and component identity.

**Buckets unlocked**:
- `packages/react-reconciler/src/__tests__/ReactFragment-test.js` (remaining non-goals)

## Phase 15: Internal Hooks Optimizations & Render-Phase Edge Cases

**Goal**: Cover internal hook behaviors that are currently closed as non-goal: bailout
paths, update queue rebasing nuances, and warning stack correctness across wrappers.

**Buckets unlocked**:
- `packages/react-reconciler/src/__tests__/ReactHooks-test.internal.js`

**Key capabilities**:
- **Render-phase update classification**: correct handling of updates scheduled during
  render vs commit, especially when a render is replayed.
- **Queue rebasing on interruption**: reconcile pending hook updates across retries.
- **Wrapper interactions**: `memo`/`forwardRef` + Suspense + StrictMode interactions that
  affect warning stacks and hook ordering.

## Phase 16: Advanced Noop Hooks Harness (Passive Unmount/Error Propagation)

**Goal**: Expand noop renderer effect semantics to match upstream expectations around
passive effect teardown ordering, deferred passive unmounts, and error propagation.

**Buckets unlocked**:
- Remaining `packages/react-reconciler/src/__tests__/ReactHooksWithNoopRenderer-test.js`

**Key capabilities**:
- **Passive destroy error surfaces**: consistent error reporting/propagation from passive
  cleanup functions.
- **Deferred passive unmount semantics**: match upstream behavior when deletions and
  reorders interact with passive effects.
- **Additional hook surfaces (as needed)**: e.g. `useImperativeHandle` if required by the
  remaining bucket.

## Phase 17: Suspense Internals + Effects Semantics Parity

**Goal**: Implement deeper Suspense boundary behaviors and commit/effects ordering
semantics that go beyond basic fallback snapshots and list coordination.

**Buckets unlocked**:
- `packages/react-reconciler/src/__tests__/ReactSuspense-test.internal.js`
- `packages/react-reconciler/src/__tests__/ReactSuspenseEffectsSemantics-test.js`
- `packages/react-reconciler/src/__tests__/ReactSuspenseyCommitPhase-test.js`

**Key capabilities**:
- **Commit ordering**: align mutations/layout/passive ordering when boundaries time out,
  recover, or partially reveal.
- **Retry/ping scheduling**: deterministic wakeups that don’t regress act() warnings.
- **Boundary bookkeeping**: track timed-out vs primary trees more faithfully.

## Phase 18: Async Actions / Entanglement (useTransition + useOptimistic)

**Goal**: Implement async action scopes and entanglement semantics for transition-driven
updates and optimistic state.

**Buckets unlocked**:
- `packages/react-reconciler/src/__tests__/ReactAsyncActions-test.js`

**Key capabilities**:
- **Action scopes**: represent an async “action” that spans microtasks and batches.
- **Entanglement**: coordinate updates across components triggered within the same action.
- **Microtask flushing model**: deterministic queue for promise continuations used by the
  action tests.

## Phase 19: Isomorphic/Async act() + Microtask Semantics

**Goal**: Implement async `act()` semantics (awaiting, microtask flushing, and promise
unwrapping) needed for isomorphic/async test suites.

**Buckets unlocked**:
- `packages/react-reconciler/src/__tests__/ReactIsomorphicAct-test.js`

**Key capabilities**:
- **Awaitable act()**: an async context manager that drains microtasks and scheduled work
  until settled.
- **Promise tracking**: detect leaked async work and warn similarly to upstream.

## Phase 20: Transition Tracing API Surface

**Goal**: Implement transition tracing primitives (names, interactions, and tracing
callbacks) and connect them to scheduler instrumentation.

**Buckets unlocked**:
- `packages/react-reconciler/src/__tests__/ReactTransitionTracing-test.js`

**Key capabilities**:
- **Tracing markers**: represent transition names/ids and store them on scheduled work.
- **Tracing callbacks**: emit start/complete/abort-style hooks with deterministic ordering.

## Explicit non-goals (likely permanent)

Some upstream buckets are intentionally out of scope for `ryact` core parity because they
target JS-specific package APIs or legacy ecosystems rather than reconciler semantics:

- `packages/react/src/__tests__/createReactClassIntegration-test.js`
- `packages/react/src/__tests__/ReactMismatchedVersions-test.js` (JS package version skew checks)

## Suite-closure “umbrella” non-goals

Some cases were previously closed as a coarse “suite-closure” non-goal because they depended
on one or more of the phases above (rather than being individually triaged). The intended path
is to reopen them in chunks as the corresponding phase lands. Common suites affected include:

- `packages/react-reconciler/src/__tests__/ReactSuspense-test.internal.js`
- `packages/react-reconciler/src/__tests__/ReactDeferredValue-test.js`
- `packages/react-reconciler/src/__tests__/ReactTransition-test.js`
- `packages/react/src/__tests__/ReactCreateElement-test.js`

