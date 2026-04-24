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

- **Rules of hooks** enforcement and invalid-hook warnings.
- **`useState` / `useReducer`** across re-renders, batching, and transitions (as asserted).
- **Effects:** passive vs layout ordering, cleanup order, strict-mode double-invoke where tests demand it.
- Add hooks **only as needed** by the manifest (`useContext`, `useId`, etc.).

## Milestone 3 — Reconciler (“fiber-like”) correctness

- Move hook state and component identity onto a **stable per-fiber (or equivalent) model**; delete renderer-global hook maps.
- **Update queues**, **lanes**, and priority integration with **`schedulyr`**.
- Proper **render vs commit** phases and **effect lists** (aligned with translated tests).

## Milestone 4 — Concurrency + Suspense (as tests demand)

- **Transitions:** `start_transition` / `useTransition` parity when manifest includes those behaviors.
- **Suspense / Lazy:** fallback timing, reveal ordering, and interruption semantics per upstream tests.

---

## “100% parity” definition (for this package)

- Every React-core-related test you track in **`tests_upstream/MANIFEST.json`** is translated and passing against **`ryact`** (with **`ryact-dom`** or other renderers only where the test belongs there).

## Non-goals (unless the manifest changes)

- Shipping a full **JSX** compiler or npm toolchain; Python **`create_element` / `h`** remains the authoring surface unless you add a separate syntax layer.
- **Browser or Node** execution of React itself — upstream remains the semantic reference, not a runtime dependency.
