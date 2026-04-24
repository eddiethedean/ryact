# ryact roadmap

Parity target: **React core** — `facebook/react` `packages/react` (elements, components, hooks, reconciler concepts, concurrent features as tests require).

What you must ship is defined by **`tests_upstream/MANIFEST.json`** (and any new entries you add when translating upstream tests). CI enforces the manifest gate.

## Product goal: two-lane developer experience (one semantic core)

We’re aiming for **two “native” authoring experiences** that both target the **same runtime semantics**:

- **React developer lane (no Python required)**:
  - Author in **JS/TS + JSX/TSX** with familiar React patterns.
  - Use an optional **JSX toolchain layer** (see Milestone 16) to compile into the `ryact` semantic core.
- **Python developer lane (no JavaScript required)**:
  - Author in **Python** with ergonomic helpers (`h`, decorators/dataclass props, etc.) and optional **PYX** (see Milestones 12–15).
  - Target the same `ryact` semantic core.

**Constraint:** these lanes must not drift. Any new surface should either be:
- **manifest-driven** (translated upstream tests assert behavior), or
- an **optional toolchain layer** that compiles to existing core semantics.

### What “same experience” means (high-level)

- **Shared mental model**: component + hooks semantics match upstream React where the manifest says we’re implemented.
- **Equivalent authoring power**: both lanes can express the same apps, with compilation/transforms bridging syntax.
- **Equivalent feedback loop**: good errors, predictable logs, test harnesses, and debugging surfaces in both lanes.

### Interop is a first-class contract

Interop means **mixed-lane apps** are supported: Python-authored trees can mount JS-authored subtrees and vice-versa, via **explicit boundary nodes** and host-level marshalling.

- **Contract doc**: `packages/ryact/docs/two_lane_interop_contract.md`
- **Non-goal by default**: “drop in arbitrary npm React components” that require upstream React/ReactDOM.

### Ecosystem growth (add-on packages)

We intend to grow a **`ryact-*` ecosystem** of add-on packages so real apps can be built without bloating `ryact` core.

- **Core stays small**: `ryact` remains the semantic core (manifest-driven correctness).
- **Add-ons carry host + UX**: routing, data-fetching, devtools, compilers, and interop runners should live in separate packages unless an upstream core test requires them in `ryact`.
- **Compatibility contract**:
  - Each add-on declares which `ryact` versions it supports (and ideally tests against them in CI).
  - Prefer “small surface area, strong tests” over broad but untested APIs.

**Initial curated add-on candidates:**

- **`ryact-jsx`**: JSX/TSX compiler/tooling (Milestone 16).
- **`ryact-pyx`**: PYX compiler/tooling (Milestone 15).
- **`ryact-interop`**: cross-lane boundary + marshalling + runners (Milestone 20).
- **`ryact-router`**: routing primitives + history adapters (host-specific integration kept out of core).
- **`ryact-devtools`**: inspection hooks + debugging UI/CLI (Milestone 18).
- **`ryact-testing-library`**: React Testing Library–style helpers built on `ryact-testkit`.

---

## Baseline today (implemented sketch)

Treat this as the floor the milestones extend; several areas are **placeholders** until translated tests drive real behavior.

### Elements & public API

- **`Element`** frozen dataclass (`type`, `props`, `key`, `ref`).
- **`create_element` / `h`** — props dict, variadic children, merged **`**kwargs`**, normalized **`children=`**, key/ref stripped from props.
- **`Component`** — optional class components; read-only **`props`**; **`render()`** runs under the same hook frame as function components (see **`hooks._render_component`**).

### Hooks (`hooks.py`)

- Implemented: **`use_state`**, **`use_reducer`**, **`use_ref`**, **`use_memo`**, **`use_callback`**, **`use_effect`**, **`use_layout_effect`** (layout currently aliases effect behavior).
- **State model:**
  - For host renderers (`ryact-dom`/`ryact-native`), state updates are still eager (mutate the slot value).
  - For the no-op reconciler snapshot path, state updates enqueue **lane-tagged pending updates** that are applied on the next render at an appropriate lane.
- **Frame model:** hooks are tracked via a single global “current hook frame”; nested hook frames are rejected.
- **Effects today:** `use_effect`/`use_layout_effect` are registered during render and executed in a commit-ish step by the no-op snapshot renderer (DOM/native are still evolving).
- **Identity model:** the no-op reconciler snapshot path owns hook identity at the root (not a full fiber tree yet).

### Reconciler (`reconciler.py`)

- **`Fiber`**, **`Root`**, **`Lane`**, **`Update`** scaffolding.
- **`create_root(..., scheduler=None)`** — optional **`schedulyr.Scheduler`** on **`Root`**; when set, **`schedule_update_on_root`** coalesces a deferred flush ( **`bind_commit`** + scheduled callback) instead of synchronous **`perform_work`** in the host.
- **`schedule_update_on_root` / `perform_work`** — queues updates and invokes a host **`render(payload)`** callback in lane-priority order (still not a full multi-pass React reconciler).
- **Lane→scheduler integration (Parity C / `schedulyr` M16)** — lanes map onto `schedulyr` numeric priorities (**sync**, **user-blocking**, **default**, **low**, **idle**). Deferred roots coalesce flushes without *priority downgrades* (a higher-priority update can reschedule the flush; a lower-priority update will not).

### Context (`context.py`)

- **`create_context`**, minimal provider/consumer helpers — propagation depth and update behavior will grow with tests.

### Concurrent / transitions (`concurrent.py`)

- **`start_transition`**, **`is_in_transition`** — minimal transition lane tagging (Milestone 4).
- **Suspense + Lazy** — minimal no-op-host semantics (Milestone 4); expanded only by translated upstream tests.

### Scheduler surface (`scheduler.py`)

- Re-exports **`schedulyr`** scheduler types for tests; **`ryact.reconciler`** can attach a **`Scheduler`** so **`ryact-dom`** defers **`perform_work`** until **`Scheduler.run_until_idle()`** (see **`ryact-dom`** README). Default remains synchronous (**`scheduler=None`**).
- **Scheduler parity is owned by `schedulyr` (full parity):**
  - **Parity B (“100% upstream `__tests__` closure”) is done** — every Jest case under upstream `facebook/react` `packages/scheduler/src/__tests__` is translated (or explicitly marked `non_goal` with rationale), tracked in `tests_upstream/scheduler/upstream_inventory.json`, and enforced by CI (**0 `pending`**; see `tests_upstream/scheduler/test_upstream_inventory_schema.py`).
  - `schedulyr` also tracks additional **production parity slices** (work-loop semantics, fairness/cooperative drain, production export surfaces, host-loop parity, native fork, postTask consolidation, curated cross-runtime suite) beyond the upstream `__tests__` inventory.
  - See **`packages/schedulyr/ROADMAP.md`** (Milestones **13–23** and parity definitions B–D).

---

## Code map (read this first when hacking)

- Public exports: `packages/ryact/src/ryact/__init__.py`
- Elements: `packages/ryact/src/ryact/element.py`
- Hooks runtime (current frame + slots): `packages/ryact/src/ryact/hooks.py`
- Update queue + scheduler coalescing: `packages/ryact/src/ryact/reconciler.py`
- Context: `packages/ryact/src/ryact/context.py`
- Concurrency placeholders: `packages/ryact/src/ryact/concurrent.py`

---

## Milestone 0 — Test translation pipeline

- Expand `tests_upstream/react/` from `packages/react/src/__tests__` (and related files) in controlled slices.
- Standardize **`ryact-testkit`** (`act`, fake timers, warnings, optional **`js2py`** helpers for JS snippets).
- Keep **`MANIFEST.json`** accurate: only **`status: "implemented"`** tests that truly pass.

**Progress (Milestone 0):**

- **React-core upstream inventory (new):**
  - Extractor: `scripts/react_jest_extract.py`
  - Inventory file: `tests_upstream/react/upstream_inventory.json` (allows `pending`; manifest remains implemented-only)
  - Inventory schema tests: `tests_upstream/react/test_upstream_inventory_schema.py`
  - Drift tools:
    - Regenerate: `python scripts/update_react_upstream_inventory.py /path/to/facebook/react`
    - Check: `python scripts/check_react_upstream_inventory.py /path/to/facebook/react`
- **Expanded `createElement` slice (implemented):**
  - Tests: `tests_upstream/react/test_create_element.py`
  - Manifest ids:
    - `react.createElement.childrenFlattening`
    - `react.createElement.childrenNormalization`
    - `react.createElement.keyAndRefExtraction`
    - `react.createElement.propsMergeSemantics`

## Milestone 1 — Elements + component model (hardening)

- Lock **element identity** rules (keys, refs, children) to upstream expectations.
- **Function + class** component update semantics beyond “happy path” smoke.
- **Dev-only warnings** where upstream asserts message text or behavior.
- **Context** propagation and consumer updates as tests require.

**Progress (Milestone 1 — Elements identity):**

- **Upstream file**: `packages/react/src/__tests__/ReactCreateElement-test.js`
- **Inventory mapping**: `tests_upstream/react/upstream_inventory.json` now tracks per-`it(...)` cases (no summary placeholders); translated cases are marked `implemented` and point at manifest ids.
- **Implementation changes**:
  - `packages/ryact/src/ryact/element.py`: **`key` is coerced to `str` when present** (matches upstream “coerces the key to a string”).
- **Translated tests**: `tests_upstream/react/test_create_element.py`
- **Manifest ids (implemented slices)**:
  - `react.createElement.childrenFlattening`
  - `react.createElement.childrenNormalization`
  - `react.createElement.childrenOverrideSemantics`
  - `react.createElement.keyAndRefExtraction`
  - `react.createElement.keyCoercionAndNull`
  - `react.createElement.propsMergeSemantics`
- **Suite-closure status (Milestones 0–4):**
  - `tests_upstream/react/upstream_inventory.json` has **0 `pending`** rows for `packages/react/src/__tests__/ReactCreateElement-test.js` (remaining cases are `implemented` or `non_goal` with rationale).

## Milestone 2 — Hooks parity (incremental)

**Purpose:** move from a “single global hook frame” sketch to **React-like hook semantics** as asserted by translated upstream tests.

**Next upstream slices to translate (recommended order):**

- `packages/react/src/__tests__/ReactHooks-test.js` → `tests_upstream/react/test_hooks_basic.py`
- `packages/react/src/__tests__/React-hooks-arity.js` → `tests_upstream/react/test_hooks_arity.py`
- `packages/react/src/__tests__/ReactHooks-test.internal.js` / `ReactHooksWithNoopRenderer-test.js` → deferred until Milestone 3 provides a no-op host.

**Checklist:**

- **Rules of hooks**
  - Reject hooks outside render; reject conditional/reordered hooks as tests require.
  - Standardize error/warning surfaces in `ryact-testkit` so assertions can match upstream.
- **State hooks**
  - `use_state` / `use_reducer`: re-render semantics (updates apply on next render, not by mutating an active frame slot).
  - Batching semantics only when a translated test asserts it.
- **Memoization hooks**
  - `use_memo` / `use_callback`: deps equality, recomputation rules, stable identity across renders.
- **Effects**
  - Stop running `use_effect` during render; represent registrations and run them in a commit-ish phase.
  - Add ordering + cleanup behavior in slices: passive vs layout, cleanup ordering, and strict-mode double invoke **only** if translated tests assert it.
- **New hooks (manifest-driven only)**
  - Introduce `use_context`, `use_id`, `use_transition`, etc. only when specific manifest rows demand them.

**Progress (Milestone 2):**

- **React-hooks-arity slice (implemented):**
  - Upstream file: `packages/react/src/__tests__/React-hooks-arity.js`
  - Tests: `tests_upstream/react/test_hooks_arity.py`
  - Manifest ids:
    - `react.hooks.arity`
- **Prereq gaps today**:
  - Global frame is still used (`packages/ryact/src/ryact/hooks.py`); nested frames are rejected.
  - DOM/native renderers still use eager state updates; reconciler-driven scheduling is only wired through the no-op snapshot path today.
- **Hook ordering slice (implemented):**
  - Upstream file: `packages/react-reconciler/src/__tests__/ReactHooks-test.internal.js`
  - Tests: `tests_upstream/react/test_hooks_basic.py`
  - Manifest ids:
    - `react.hooks.ordering`
- **Suite-closure status (Milestones 0–4):**
  - `tests_upstream/react/upstream_inventory.json` has **0 `pending`** rows for:
    - `packages/react-reconciler/src/__tests__/ReactHooks-test.internal.js`
    - `packages/react-reconciler/src/__tests__/ReactHooksWithNoopRenderer-test.js`
- **Tracking**:
  - Inventory: `tests_upstream/react/upstream_inventory.json` (per-case)
  - Manifest: add `react.hooks.*` ids only when a coherent slice is translated and passing

## Milestone 3 — Reconciler (“fiber-like”) correctness

**Purpose:** introduce a minimal “fiber-like” model so identity, updates, and effects can be tested in a deterministic host without relying on DOM/native.

**Prerequisites (inputs to this milestone):**

- Existing host renderers (`ryact-dom`, `ryact-native`) are useful for end-to-end smoke, but this milestone should be driven by a deterministic **no-op host**.
- Hooks must move from “renderer-owned slots” to “tree-owned slots” to support reordering/identity rules.

**Next upstream slices to translate (recommended order):**

- `packages/react-reconciler/src/__tests__/ReactHooksWithNoopRenderer-test.js` → `tests_upstream/react/test_noop_renderer_hooks.py`
- `packages/react-reconciler/src/__tests__/ReactIncremental-test.js` / reconciler correctness tests (only once we can represent render/commit phases)

**Architecture transition checklist:**

- **No-op host (test harness)**
  - Add deterministic host utilities (likely under `packages/ryact-testkit`) to “mount” a root and record commits without DOM.
  - Stable tree serialization for assertions.
- **Per-fiber identity**
  - Introduce stable component identity per node in a tree (fiber or equivalent).
  - Move hook slot lists onto the per-node structure; eliminate renderer-global hook maps.
- **Update queues + lanes**
  - Encode update queue semantics on fibers; model sync vs deferred work.
  - Keep lane-to-`schedulyr` priority mapping centralized; do not fork host policy in renderers.
- **Render vs commit**
  - Separate render (compute next tree + effects list) from commit (apply host mutations).
  - Effects must run post-commit (unblocks Milestone 2 effect semantics).
- **Effect lists**
  - Maintain explicit effect lists (passive vs layout) with deterministic ordering/cleanup.

**Progress (Milestone 3):**

- **No-op host (test harness):**
  - `packages/ryact-testkit/src/ryact_testkit/noop_renderer.py` (`create_noop_root`, deterministic commit log)
- **Per-fiber hook identity (noop host):**
  - Hook slots live on `Fiber.hooks` and are carried via `alternate` matching by (index, key, type).
- **Render/commit split + effect lists (noop host):**
  - Render produces `NoopWork(snapshot, insertion/layout/passive effect lists, finished fiber tree)`.
  - Commit publishes snapshot, runs insertion → layout → passive effects, then swaps `root.current`.
  - Implemented in `packages/ryact/src/ryact/reconciler.py` and `packages/ryact-testkit/src/ryact_testkit/noop_renderer.py`.
- **Translated tests (NoopRenderer slice):**
  - Upstream: `packages/react-reconciler/src/__tests__/ReactHooksWithNoopRenderer-test.js`
  - Tests: `tests_upstream/react/test_noop_renderer_hooks.py`
  - Manifest ids:
    - `react.noop.hooksSmoke`

## Milestone 4 — Concurrency + Suspense (as tests demand)

**Purpose:** add concurrency surfaces only when the reconciler can represent interruption/replay and Suspense can be asserted deterministically.

**Prerequisites:**

- Milestone 3 provides a no-op host + fiber-ish identity and a render/commit split.
- Effects are commit-driven (not executed during render).

**Next upstream slices to translate (curated “first” set):**

- Transitions:
  - `packages/react-reconciler/src/__tests__/ReactTransition-test.js` → `tests_upstream/react/test_transitions.py`
- Lazy:
  - `packages/react-reconciler/src/__tests__/ReactLazy-test.internal.js` (and/or equivalent) → `tests_upstream/react/test_lazy.py`
- Suspense:
  - `packages/react-reconciler/src/__tests__/ReactSuspenseFallback-test.js` / `ReactSuspense-test.internal.js` → `tests_upstream/react/test_suspense.py`

**Checklist:**

- **Transitions**
  - Define lane/priority behavior for transition updates (manifest-driven).
  - Implement `start_transition` / `useTransition` only when the first translated test asserts observable behavior.
- **Suspense**
  - Fallback timing + reveal ordering.
  - Interruption semantics (render can be abandoned and retried).
- **Lazy**
  - Resolution caching and identity rules.
  - Interaction with Suspense boundaries.

**Progress (Milestone 4):**

- **Transitions (first slice):**
  - Upstream: `packages/react-reconciler/src/__tests__/ReactTransition-test.js`
  - Tests: `tests_upstream/react/test_transitions.py`
  - Manifest ids:
    - `react.concurrent.transitionsBasic`
  - Invariants now asserted:
    - Transition updates are scheduled on a distinct lane and commit after normal-priority work.
- **Suspense (first slice):**
  - Upstream: `packages/react-reconciler/src/__tests__/ReactSuspenseFallback-test.js`
  - Tests: `tests_upstream/react/test_suspense.py`
  - Manifest ids:
    - `react.concurrent.suspenseBasic`
  - Invariants now asserted:
    - A Suspense boundary can show fallback when a child suspends and later reveal when resolved.
- **Lazy (first slice):**
  - Upstream: `packages/react-reconciler/src/__tests__/ReactLazy-test.internal.js`
  - Tests: `tests_upstream/react/test_lazy.py`
  - Manifest ids:
    - `react.concurrent.lazyBasic`
  - Invariants now asserted:
    - Lazy resolution is cached and can resolve synchronously without suspending.
- **Additional concurrency-era surfaces (first slices):**
  - `useTransition` pending flag:
    - Tests: `tests_upstream/react/test_transitions_use_transition.py`
    - Manifest ids:
      - `react.concurrent.useTransition.basicPending`
  - `useDeferredValue` (minimal):
    - Tests: `tests_upstream/react/test_deferred_value.py`
    - Manifest ids:
      - `react.concurrent.useDeferredValue.basic`
  - `useSyncExternalStore` (minimal):
    - Tests: `tests_upstream/react/test_sync_external_store.py`
    - Manifest ids:
      - `react.concurrent.useSyncExternalStore.basic`
  - `useInsertionEffect` ordering (noop host):
    - Tests: `tests_upstream/react/test_insertion_effect.py`
    - Manifest ids:
      - `react.hooks.insertionEffect`
- **Suite-closure status (Milestones 0–4):**
  - `tests_upstream/react/upstream_inventory.json` has **0 `pending`** rows for the curated Milestone 4 suites:
    - `packages/react-reconciler/src/__tests__/ReactTransition-test.js`
    - `packages/react-reconciler/src/__tests__/ReactSuspenseFallback-test.js`
    - `packages/react-reconciler/src/__tests__/ReactSuspense-test.internal.js`
    - `packages/react-reconciler/src/__tests__/ReactLazy-test.internal.js`
    - `packages/react-reconciler/src/__tests__/ReactDeferredValue-test.js`
    - `packages/react-reconciler/src/__tests__/useSyncExternalStore-test.js`

---

## Milestone 5 — Child reconciliation (diffing, keys, placement)

**Purpose:** move from “snapshot rendering” to **React-like reconciliation**: keyed children, stable identity, minimal host mutations, and deterministic placement/deletion semantics.

**Prerequisites:**

- Milestone 3: deterministic no-op host + commit-ish effects.
- A representation of host mutations in the no-op host (insert/move/delete) that can be asserted deterministically.

**Next upstream slices to translate (recommended order):**

- Children + keys:
  - `packages/react/src/__tests__/ReactChildren-test.js`
  - `packages/react/src/__tests__/ReactElementClone-test.js` (key propagation/override edge cases)
- Reconciliation behavior (no-op host / reconciler):
  - `packages/react-reconciler/src/__tests__/ReactIncremental-test.js` (or current upstream equivalent)
  - `packages/react-reconciler/src/__tests__/ReactNoopRendererAct-test.js` (only once act/flush semantics need it)

**Checklist:**

- **Keyed list diffing**
  - Insertions, deletions, moves, and reorders match upstream expectations.
  - Stable per-node identity across reorders when keys are stable.
- **Placement + deletion effects**
  - Deterministic commit log for “host operations” (not just snapshots).
  - Correct cleanup ordering on deletion (hooks + effects).

**Progress (Milestone 5):**

- **Deterministic noop host op log (new):**
  - `packages/ryact-testkit/src/ryact_testkit/noop_renderer.py`
  - `NoopContainer.ops`: list of host ops (`insert`/`move`/`delete`/`updateProps`/`text`)
  - Test helpers:
    - `NoopRoot.get_ops()`
    - `NoopRoot.clear_ops()`
    - `NoopRoot.get_children_snapshot()`
- **Host instance tree (noop host):**
  - No-op commit now maintains a stable `container.host_root` instance tree and applies ops instead of only replacing snapshots.
- **Key-first reconciliation primitive (core + noop host):**
  - `packages/ryact/src/ryact/reconciler.py`: `reconcile_key_first_indices(...)` computes index-level `insert`/`move`/`delete`
  - No-op host uses this routine to preserve identity across keyed reorders.
- **Translated tests (first keyed ops slice):**
  - Tests: `tests_upstream/react/test_children_reconciliation.py`
  - Manifest ids:
    - `react.reconcile.keys.insertMoveDelete`
  - Inventory mapping updated in `tests_upstream/react/upstream_inventory.json` (ReactChildren/ReactElementClone + one ReactIncremental row mapped to this slice).

## Milestone 6 — Class lifecycles + error boundaries

**Purpose:** make class components and errors behave like upstream, including mount/update/unmount ordering and recovery via error boundaries.

**Prerequisites:**

- Milestone 5 (or equivalent): commit phase that can attach/detach instances deterministically.

**Next upstream slices to translate:**

- Class component semantics:
  - `packages/react/src/__tests__/ReactES6Class-test.js`
  - `packages/react/src/__tests__/ReactClassEquivalence-test.js`
- Error boundaries:
  - `packages/react-reconciler/src/__tests__/ReactErrorBoundaries-test.internal.js` (or current equivalent)

**Checklist:**

- **Lifecycle ordering**
  - `componentDidMount`, `componentDidUpdate`, `componentWillUnmount`
  - `getDerivedStateFromProps`, `getSnapshotBeforeUpdate` only when tests demand them
- **Error boundaries**
  - `componentDidCatch` / `getDerivedStateFromError` as asserted by translated tests
  - Recovery behavior (retry render, preserve boundaries, deterministic commits)

**Progress (Milestone 6):**

- **Class lifecycle ordering (noop host, first slice):**
  - Upstream: `packages/react-reconciler/src/__tests__/ReactIncrementalSideEffects-test.js`
  - Tests: `tests_upstream/react/test_class_lifecycles.py`
  - Manifest ids:
    - `react.class.lifecycles.basicOrdering`
  - Invariants asserted:
    - `componentDidMount` runs after initial commit
    - `componentDidUpdate` runs after update commit
    - `componentWillUnmount` runs when deleted (even when nested)
- **Error boundaries (noop host, first slice):**
  - Upstream: `packages/react-reconciler/src/__tests__/ErrorBoundaryReconciliation-test.internal.js`
  - Tests: `tests_upstream/react/test_error_boundaries.py`
  - Manifest ids:
    - `react.errorBoundaries.basicRecovery`
  - Invariants asserted:
    - `getDerivedStateFromError` can flip boundary state and recover rendering
    - `componentDidCatch` runs during commit for the captured error
- **Runtime wiring (enables both slices):**
  - `Fiber.state_node` now persists class instances across renders (noop reconciler path)
  - No-op commit runs a deterministic `commit_callbacks` list and detects removed fibers to call `componentWillUnmount`

## Milestone 7 — StrictMode + dev-only semantics

**Purpose:** match upstream dev-time semantics that affect correctness: StrictMode replay/double-invoke, warnings, and invariant checks that tests assert.

**Prerequisites:**

- Milestone 5+: reconciliation/commit order must be deterministic enough to replay safely.

**Next upstream slices to translate:**

- StrictMode suites (upstream equivalent names vary by version):
  - `packages/react/src/__tests__/ReactStrictMode-test.js` (or internal equivalent)
  - Hook strict replay suites inside `ReactHooks-test.internal.js`

**Checklist:**

- **Strict replay**
  - Double-invocation behavior for render/effects *only* where tests assert it.
- **Warnings + invariants**
  - Standardize warning capture in `ryact-testkit` so message text can be asserted.

**Progress (Milestone 7):**

- **StrictMode (minimal DEV replay slice):**
  - Upstream: `packages/react-reconciler/src/__tests__/ReactHooks-test.internal.js`
  - Tests: `tests_upstream/react/test_strict_mode.py`
  - Manifest ids:
    - `react.strictMode.basicReplay`
  - Invariants asserted:
    - StrictMode causes **double-invocation of mount renders** for hook components (noop host, DEV-only)
    - No additional effect replay semantics are implemented yet (only as upstream slices demand)
- **Dev warnings (minimal act warning slice):**
  - Upstream: `packages/react-reconciler/src/__tests__/ReactActWarnings-test.js`
  - Tests: `tests_upstream/react/test_dev_warnings.py`
  - Manifest ids:
    - `react.devWarnings.basic`
  - Invariants asserted:
    - `ryact-testkit.act()` warns when the act environment flag is not enabled
- **Runtime wiring (enables both slices):**
  - `StrictMode` is represented as a special wrapper host type (`__strict_mode__`) for the noop reconciler
  - DEV flag is test-controlled via `packages/ryact/src/ryact/dev.py`
  - No-op reconciler threads a `strict` context and double-invokes function component mounts when strict+DEV is enabled

## Milestone 8 — Refs, portals, and deeper context semantics

**Purpose:** fill major “commit-time wiring” gaps: refs attach/detach timing, portals (if adopted), and context propagation/bailouts beyond the current minimal helpers.

**Prerequisites:**

- Milestone 5: host mutation model and commit-time ordering.

**Next upstream slices to translate:**

- Refs:
  - `packages/react/src/__tests__/ReactCreateRef-test.js`
- Context:
  - `packages/react/src/__tests__/ReactContextValidator-test.js`
  - additional `ReactContext*` suites as they appear in inventory
- Portals (only if/when a host needs them):
  - `packages/react-dom/src/__tests__/ReactDOMPortal-test.js` (belongs in `ryact-dom`, but drives core semantics)

**Checklist:**

- **Refs**
  - Callback refs vs object refs, cleanup ordering, commit timing.
- **Context**
  - Provider nesting, propagation depth, bailout rules, and updates across lanes as asserted.
- **Portals (optional)**
  - Only add once a translated suite requires it; keep core+host boundaries explicit.

**Progress (Milestone 8):**

- **Refs (first slice):**
  - Upstream: `packages/react/src/__tests__/ReactCreateRef-test.js`
  - Tests: `tests_upstream/react/test_refs_basic.py`
  - Manifest ids:
    - `react.refs.basicAttachDetach`
  - Invariants asserted:
    - `create_ref()` returns an object with `.current`
    - Object and callback refs attach on commit and detach on unmount (noop host)
    - Invalid ref objects warn in dev when committed
- **Context validator (first slice):**
  - Upstream: `packages/react/src/__tests__/ReactContextValidator-test.js`
  - Tests: `tests_upstream/react/test_context_validator.py`
  - Manifest ids:
    - `react.context.validator.basic`
  - Invariants asserted:
    - `contextType = None` does not warn
    - Invalid `contextType` warns in dev
- **Portals (first slice; `ryact-dom`):**
  - Upstream: `packages/react-dom/src/__tests__/ReactDOMPortal-test.js`
  - Tests: `tests_upstream/react_dom/test_portals_basic.py`
  - Manifest ids:
    - `react_dom.portals.basic`
  - Invariants asserted:
    - Portal children render into the target container and are cleared on unmount
- **Runtime wiring:**
  - `ryact-testkit` noop host now commits the root snapshot as a single child under `container.host_root`, enabling ref attachment to stable host instances
  - `ryact` core exports `create_ref()` / `Ref` and a minimal `create_portal()` (`__portal__`)

## Milestone 9 — Component wrapper types (Fragment, memo, forwardRef)

**Purpose:** support common React element “type wrappers” that affect reconciliation and ref forwarding.

**Prerequisites:**

- Milestone 5: reconciliation for composite/host trees.

**Next upstream slices to translate:**

- `packages/react/src/__tests__/ReactFragment-test.js` (or current equivalent)
- `packages/react/src/__tests__/ReactMemo-test.js` (or current equivalent)
- `packages/react/src/__tests__/forwardRef-test.js` (or current equivalent)

**Checklist:**

- **Fragment**
  - Children flattening semantics + key behavior in reconciliation.
- **memo**
  - Props comparison + bailout semantics as asserted.
- **forwardRef**
  - Ref forwarding + identity rules.

**Progress (Milestone 9):**

- **Fragment (first slice):**
  - Upstream: `packages/react-reconciler/src/__tests__/ReactFragment-test.js`
  - Tests: `tests_upstream/react/test_fragment.py`
  - Manifest ids:
    - `react.fragment.basic`
  - Invariants asserted:
    - Fragment is transparent in host output (children are flattened into the parent)
    - Changing fragment shape / key causes remount (state is not preserved across those changes)
- **Runtime wiring:**
  - `ryact` exports `Fragment` + `fragment(...)`
  - No-op reconciler flattens fragment snapshots and keeps fragment as a real fiber node
  - `ryact-dom` flattens fragment children during rendering

## Milestone 10 — Advanced hooks + external store integration

**Purpose:** add “modern” hook surfaces only when inventory + manifest slices require them, with deterministic semantics in the no-op host.

**Next upstream slices to translate (manifest-driven):**

- `useDeferredValue`, `useTransition` (hook form), `useId`
- `useSyncExternalStore` (core correctness; DOM integration belongs in host packages)
- `useInsertionEffect` (only once style-insertion ordering is asserted)

**Checklist:**

- Add each hook behind a translated slice with a single manifest id per coherent group.
- Keep host-specific behavior in host packages (`ryact-dom`, `ryact-native`) unless the suite is core-only.

**Progress (Milestone 10):**

- **React DOM upstream inventory (new)**
  - Inventory: `tests_upstream/react_dom/upstream_inventory.json`
  - Schema test: `tests_upstream/react_dom/test_react_dom_upstream_inventory_schema.py`
  - Scripts:
    - `scripts/react_dom_jest_extract.py`
    - `scripts/update_react_dom_upstream_inventory.py`
    - `scripts/check_react_dom_upstream_inventory.py`
- **useId (first slice)**
  - Upstream: `packages/react-dom/src/__tests__/ReactDOMUseId-test.js`
  - Tests: `tests_upstream/react_dom/test_use_id_basic.py`
  - Manifest ids:
    - `react_dom.useId.basic`
  - Runtime wiring:
    - `ryact` exports `use_id()` (`packages/ryact/src/ryact/hooks.py`, `packages/ryact/src/ryact/__init__.py`)
    - No-op reconciler provides a per-render deterministic id allocator (threaded through `_render_with_hooks`) in `packages/ryact/src/ryact/reconciler.py`
  - Invariants asserted:
    - Ids are stable across re-renders for a given component instance
    - Sibling components get distinct ids
    - Under DEV StrictMode replay, committed ids remain stable across renders
- **useInsertionEffect (expanded slice)**
  - Upstream: `packages/react-reconciler/src/__tests__/ReactHooksWithNoopRenderer-test.js`
  - Tests: `tests_upstream/react/test_insertion_effect.py`
  - Manifest ids:
    - `react.hooks.insertionEffect`
  - Invariants asserted:
    - Insertion effects observe the updated committed snapshot on update (i.e. they run after snapshot publication)

## Milestone 11 — Core vs host boundary + SSR/hydration (explicitly scoped)

**Purpose:** make the roadmap explicit about which “big React” areas live outside `ryact` core and when we’d adopt them.

**Checklist:**

- **Core vs host split**
  - Document which suites are expected to live under `tests_upstream/react/` vs `tests_upstream/react_dom/` (and `tests_upstream/scheduler/`).
  - **Suite ownership rules (source of truth):**
    - `tests_upstream/react/*` — renderer-agnostic **core semantics**: elements, hooks, reconciler behavior (incl. no-op host).
    - `tests_upstream/react_dom/*` — **DOM host semantics**: host props/attributes, events, portals, roots, SSR surfaces.
    - `tests_upstream/scheduler/*` — `schedulyr` parity.
  - **Translation placement guidelines:**
    - If the upstream test imports or assumes DOM APIs/serialization (`react-dom`, host config, attribute rules), translate under `react_dom`.
    - If it asserts semantics that should hold across hosts, translate under `react`.
- **SSR/hydration (optional, future)**
  - Only adopt if/when you add manifest entries for it.
  - Treat SSR/hydration semantics as host-driven (`ryact-dom`) with core primitives added only as demanded.
  - Hydration stays **out of scope** unless a manifest id is added for it (avoid “accidental hydration” scope creep).

---

## Optional ergonomics milestones (Python-first interface)

## Milestone 12 — Pythonic authoring surface (ergonomics, not semantics)

**Purpose:** provide a more idiomatic Python API on top of `create_element`/hooks without changing the underlying semantics. This is optional and should not block parity milestones.

**Checklist:**

- **Stable public aliases**
  - Finalize and document `h(...)` as a first-class alias to `create_element(...)` (or rename/standardize if desired).
- **Props ergonomics**
  - Typed helpers for `className`/`style`/event-ish props (host-specific), while keeping `ryact` core host-agnostic.
  - Consistent conventions for `children` passing (positional vs `children=`).
- **Ref ergonomics (future, manifest-driven)**
  - Python-friendly `create_ref()` and callback-ref helpers once ref tests require it.

**Progress (Milestone 12):**

- **Docs:**
  - `packages/ryact/README.md` now documents `h(...)` as first-class, prefers positional children (while allowing `children=`), and includes `create_ref()` + callback ref examples.
- **`ryact-dom` authoring helpers (host-specific):**
  - Added `packages/ryact-dom/src/ryact_dom/props.py` with `cx(...)`, `style(...)`/`style_dict(...)`, and `on(event, handler)` helpers.
  - Exported from `packages/ryact-dom/src/ryact_dom/__init__.py`.
- **Non-upstream tests (ergonomics):**
  - Added `tests_property/test_ryact_dom_props_helpers.py`.

## Milestone 13 — Python-first component patterns (decorators + dataclasses)

**Purpose:** offer ergonomic patterns that feel native in Python, with opt-in helpers and clear boundaries from React semantics.

**Checklist:**

- **`@component` decorator (optional)**
  - Declarative wrapper for function components that preserves signature/type hints and improves error messages.
- **Dataclass props pattern**
  - Optional helpers to accept `@dataclass` props and convert to `dict` for `create_element`.
  - Keep runtime behavior identical to passing a normal props dict.
- **Default-props pattern**
  - Provide a Pythonic way to express defaults (dataclass defaults, `TypedDict` defaults), without inventing new React semantics.

## Milestone 14 — Type-driven public API (pyright/mypy-friendly)

**Purpose:** make the public `ryact` API pleasant to use with type checkers, while keeping runtime lightweight.

**Checklist:**

- **Element typing**
  - Stronger `Element` typing for `type`, `props`, and `children` where it helps users, without over-constraining internals.
- **Component typing**
  - Generic typing for function components and `Component` subclasses.
- **Hook typing**
  - Improve hook return types and callable signatures (`use_state`, `use_reducer`, refs, memo hooks) as slices expand.

## Milestone 15 — Python template syntax layers (PYX / optional)

**Purpose:** add an optional XML-like template language that compiles to `create_element`/`h`, as a separate toolchain concern.

**Checklist:**

- **Compiler boundary**
  - Keep transforms out of `ryact` core runtime; prefer a separate package or `scripts/` tooling.
- **Round-trip tests**
  - Golden-file snapshots for compilation output and runtime equivalence tests against handwritten `create_element` trees.
- **Gating**
  - Remains a non-goal unless you add manifest entries that require it.

## Milestone 16 — JSX toolchain layer (optional)

**Purpose:** add an optional JSX/TSX-to-Python transform that outputs `create_element`/`h` calls, as a separate toolchain concern.

**Checklist:**

- **Compiler boundary**
  - Keep transforms out of `ryact` core runtime; prefer a separate package or `scripts/` tooling.
- **Golden tests**
  - Snapshot the generated Python output and run a small runtime smoke suite under `ryact-testkit`.
- **Gating**
  - Remains a non-goal unless you add manifest entries that require it.

## Milestone 17 — React-dev tooling layer (JS/TS DX)

**Purpose:** make a React developer productive without learning Python by providing a familiar JS/TS workflow that targets `ryact` semantics.

**Checklist:**

- **Project scaffolding**
  - A `create-ryact-app` style starter (or templates) for JSX/TSX projects.
  - Conventional structure (src/, tests/, build output).
- **Build + transform**
  - Compile JSX/TSX into a representation that can be executed against the `ryact` semantic core.
  - **Source maps** and stable stack traces that map back to JSX/TSX.
- **Runtime integration**
  - A minimal “host runner” contract for executing compiled output against a host (`ryact-dom`, `ryact-native`, or no-op).

## Milestone 18 — Debugging + devtools parity surfaces (both lanes)

**Purpose:** ensure both React devs and Python devs get a comparable debugging experience: warnings, component stacks, and inspection hooks.

**Checklist:**

- **Component stack traces**
  - Deterministic component stack formatting for errors/warnings asserted by tests.
- **Warning contracts**
  - Centralize warning capture/formatting in `ryact-testkit` and expose a stable user-facing API.
- **Inspection hooks (future)**
  - Optional integration points for DevTools-like inspection (tree, props/state, hooks) once the reconciler can represent it.

## Milestone 19 — Cross-language app parity (examples + golden fixtures)

**Purpose:** prevent drift between the two lanes by maintaining “the same app” implemented both ways and verified equivalently.

**Checklist:**

- **Paired examples**
  - A small set of canonical apps implemented in:
    - Python (`create_element`/PYX) and
    - JSX/TSX (toolchain output)
- **Golden equivalence**
  - Assert that both versions produce identical no-op snapshots/commit logs for the same scenarios.

## Milestone 20 — Cross-lane interop (mixed trees)

**Purpose:** make the two lanes interoperable in one app via a stable, testable boundary contract.

**Contract:** `packages/ryact/docs/two_lane_interop_contract.md`

**Checklist:**

- **Boundary primitives**
  - Define explicit boundary nodes for “JS subtree” and “Python subtree” (names TBD).
  - Enforce a conservative marshalling contract (JSON-ish + explicit escapes) across the boundary.
- **Host execution**
  - `ryact-testkit`: deterministic stub runner for foreign components (parity tests).
  - `ryact-dom`: host-level runner contract for executing compiled JS/TSX output and calling into Python.
- **Paired interop fixtures**
  - Extend Milestone 19 examples with mixed-lane versions:
    - Python root → JS leaf
    - JS root → Python leaf
- **Explicit out-of-scope**
  - Using arbitrary npm components that expect upstream React/ReactDOM remains a non-goal unless the manifest changes.

## “100% parity” definition (for this package)

- Every React-core-related test you track in **`tests_upstream/MANIFEST.json`** is translated and passing against **`ryact`** (with **`ryact-dom`** or other renderers only where the test belongs there).

## Non-goals (unless the manifest changes)

- Shipping a required **JSX** compiler or npm toolchain; Python **`create_element` / `h`** remains the default authoring surface unless you add an optional syntax layer.
- **Browser or Node** execution of React itself — upstream remains the semantic reference, not a runtime dependency.
