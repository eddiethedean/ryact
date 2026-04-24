# ryact roadmap

Parity target: **React core** — `facebook/react` `packages/react` (elements, components, hooks, reconciler concepts, concurrent features as tests require).

What you must ship is defined by **`tests_upstream/MANIFEST.json`** (and any new entries you add when translating upstream tests). CI enforces the manifest gate.

---

## Baseline today (implemented sketch)

Treat this as the floor the milestones extend; several areas are **placeholders** until translated tests drive real behavior.

### Elements & public API

- **`Element`** frozen dataclass (`type`, `props`, `key`, `ref`).
- **`create_element` / `h`** — props dict, variadic children, merged **`**kwargs`**, normalized **`children=`**, key/ref stripped from props.
- **`Component`** — optional class components; read-only **`props`**; **`render()`** runs under the same hook frame as function components (see **`hooks._render_component`**).

### Hooks (`hooks.py`)

- Implemented: **`use_state`**, **`use_reducer`**, **`use_ref`**, **`use_memo`**, **`use_callback`**, **`use_effect`**, **`use_layout_effect`** (layout currently aliases effect behavior).
- **State model:** hook state lives in a plain Python `list[Any]` supplied by the renderer; `set_state`/`dispatch` mutate list slots directly (no scheduling/invalidation yet).
- **Frame model:** hooks are tracked via a single global “current hook frame”; nested hook frames are rejected.
- **Effects today:** `use_effect` runs *during render* (stores cleanup + deps), not in a separate commit phase yet.
- **Identity model:** hook lists are owned by renderers today (not by a fiber tree) — sufficient for early tests, but not correct for full rules-of-hooks, strict-mode replay, or concurrent rendering semantics.

### Reconciler (`reconciler.py`)

- **`Fiber`**, **`Root`**, **`Lane`**, **`Update`** scaffolding.
- **`create_root(..., scheduler=None)`** — optional **`schedulyr.Scheduler`** on **`Root`**; when set, **`schedule_update_on_root`** coalesces a deferred flush ( **`bind_commit`** + scheduled callback) instead of synchronous **`perform_work`** in the host.
- **`schedule_update_on_root` / `perform_work`** — queues updates and commits by invoking a host **`render(payload)`** callback with the **last** payload (early “commit only” model; not a multi-pass React reconciler yet).
- **Lane→scheduler integration (Parity C / `schedulyr` M16)** — lanes map onto `schedulyr` numeric priorities (**sync**, **user-blocking**, **default**, **low**, **idle**). Deferred roots coalesce flushes without *priority downgrades* (a higher-priority update can reschedule the flush; a lower-priority update will not).

### Context (`context.py`)

- **`create_context`**, minimal provider/consumer helpers — propagation depth and update behavior will grow with tests.

### Concurrent / transitions (`concurrent.py`)

- **`start_transition`**, **`is_in_transition`**, **`Suspense`**, **`Lazy`** — structural placeholders; semantics follow **`ryact` milestone 4** as upstream tests land.

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
  - Hook slots are renderer-owned and tracked via a single global frame (`packages/ryact/src/ryact/hooks.py`).
  - Effects run during render (placeholder).
- **Tracking**:
  - Inventory: `tests_upstream/react/upstream_inventory.json` (per-case)
  - Manifest: add `react.hooks.*` ids only when a coherent slice is translated and passing

## Milestone 3 — Reconciler (“fiber-like”) correctness

**Purpose:** introduce a minimal “fiber-like” model so identity, updates, and effects can be tested in a deterministic host without relying on DOM/native.

**Prerequisites (inputs to this milestone):**

- Existing host renderers (`ryact-dom`, `ryact-native`) are useful for end-to-end smoke, but this milestone should be driven by a deterministic **no-op host**.
- Hooks must move from “renderer-owned slots” to “tree-owned slots” to support reordering/identity rules.

**Next upstream slices to translate (recommended order):**

- `packages/react/src/__tests__/ReactHooksWithNoopRenderer-test.js` (or current upstream equivalent) → `tests_upstream/react/test_noop_renderer_hooks.py`
- `packages/react/src/__tests__/ReactIncremental-test.js` / reconciler correctness tests (only once we can represent render/commit phases)

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

- `packages/ryact/src/ryact/reconciler.py` is currently a root-level “commit last payload” model (no per-node identity).

## Milestone 4 — Concurrency + Suspense (as tests demand)

**Purpose:** add concurrency surfaces only when the reconciler can represent interruption/replay and Suspense can be asserted deterministically.

**Prerequisites:**

- Milestone 3 provides a no-op host + fiber-ish identity and a render/commit split.
- Effects are commit-driven (not executed during render).

**Next upstream slices to translate (curated “first” set):**

- Transitions:
  - `packages/react/src/__tests__/ReactTransition-test.js` (or current upstream equivalent) → `tests_upstream/react/test_transitions.py`
- Lazy:
  - `packages/react/src/__tests__/ReactLazy-test.js` / `ReactLazy-test.internal.js` → `tests_upstream/react/test_lazy.py`
- Suspense:
  - `packages/react/src/__tests__/ReactSuspense-test.js` / `ReactSuspense-test.internal.js` → `tests_upstream/react/test_suspense.py`

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

- `packages/ryact/src/ryact/concurrent.py` is placeholder-only today; do not expand without translated tests.

---

## “100% parity” definition (for this package)

- Every React-core-related test you track in **`tests_upstream/MANIFEST.json`** is translated and passing against **`ryact`** (with **`ryact-dom`** or other renderers only where the test belongs there).

## Non-goals (unless the manifest changes)

- Shipping a full **JSX** compiler or npm toolchain; Python **`create_element` / `h`** remains the authoring surface unless you add a separate syntax layer.
- **Browser or Node** execution of React itself — upstream remains the semantic reference, not a runtime dependency.
