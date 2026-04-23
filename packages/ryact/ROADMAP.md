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
- **Identity model:** hook lists are owned by **renderers** today (`id(component)` / class identity), not by a fiber tree — sufficient for early tests, wrong for full rules-of-hooks and concurrent replay semantics.

### Reconciler (`reconciler.py`)

- **`Fiber`**, **`Root`**, **`Lane`**, **`Update`** scaffolding.
- **`create_root(..., scheduler=None)`** — optional **`schedulyr.Scheduler`** on **`Root`**; when set, **`schedule_update_on_root`** coalesces a deferred flush ( **`bind_commit`** + scheduled callback) instead of synchronous **`perform_work`** in the host.
- **`schedule_update_on_root` / `perform_work`** — queues updates, sorts by lane priority, then commits by invoking a **`render(payload)`** callback with the **last** payload (early model; not a multi-pass React reconciler yet).

### Context (`context.py`)

- **`create_context`**, minimal provider/consumer helpers — propagation depth and update behavior will grow with tests.

### Concurrent / transitions (`concurrent.py`)

- **`start_transition`**, **`is_in_transition`**, **`Suspense`**, **`Lazy`** — structural placeholders; semantics follow **`ryact` milestone 4** as upstream tests land.

### Scheduler surface (`scheduler.py`)

- Re-exports **`schedulyr`** scheduler types for tests; **`ryact.reconciler`** can attach a **`Scheduler`** so **`ryact-dom`** defers **`perform_work`** until **`Scheduler.run_until_idle()`** (see **`ryact-dom`** README). Default remains synchronous (**`scheduler=None`**).
- Full upstream **`packages/scheduler/src/__tests__`** parity (all JS test files ported and passing) is owned by **`schedulyr`** — see **`packages/schedulyr/ROADMAP.md`** Milestones **4–10**.

---

## Milestone 0 — Test translation pipeline

- Expand `tests_upstream/react/` from `packages/react/src/__tests__` (and related files) in controlled slices.
- Standardize **`ryact-testkit`** (`act`, fake timers, warnings, optional **`js2py`** helpers for JS snippets).
- Keep **`MANIFEST.json`** accurate: only **`status: "implemented"`** tests that truly pass.

## Milestone 1 — Elements + component model (hardening)

- Lock **element identity** rules (keys, refs, children) to upstream expectations.
- **Function + class** component update semantics beyond “happy path” smoke.
- **Dev-only warnings** where upstream asserts message text or behavior.
- **Context** propagation and consumer updates as tests require.

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
