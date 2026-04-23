# ryact-dom roadmap

Parity targets:

- **Client:** `facebook/react` `packages/react-dom` (createRoot, host updates, events).
- **Server:** `react-dom/server` (or the subset upstream tests lock in).

The **gate** for what must be implemented is still `tests_upstream/MANIFEST.json` plus whatever you add when translating new upstream files.

---

## Baseline today (implemented sketch)

Use this as the starting point for milestones below; replace “sketch” pieces as tests demand.

- **`create_root` / `Root.render`** — commits through `ryact`’s root scheduler (`schedule_update_on_root` / `perform_work`).
- **Deterministic host** — `Container`, `ElementNode`, `TextNode`, `SyntheticEvent` in `dom.py` for assertions without a real browser.
- **Render path** — recursive expansion of host elements; function and `ryact.Component` class components via `ryact.hooks._render_component`.
- **Commit model** — today the client clears the container and rebuilds the tree on each commit (no incremental host diff yet).
- **Events (early)** — bubbling, `stopPropagation`, `currentTarget`; listener props normalized in `html_props.py` (e.g. `onClick` and Pythonic `on_click`).
- **SSR placeholder** — `render_to_string` with basic attribute rules (e.g. `class` / `className` / `class_name`, `data_*` → `data-*`); not full HTML escaping / edge-case parity.

---

## Milestone 0 — Tests + deterministic harness

- Grow `tests_upstream/react_dom/` from targeted slices of `packages/react-dom/src/__tests__`.
- Ensure **`act()`** (via `ryact-testkit`) drains scheduler work and effects in a stable order when tests assert on timing.
- Keep the in-Python DOM host **stable** (predictable structure for pytest assertions).

## Milestone 1 — Host config + reconciliation

- Define a small **host config** surface (create/update/delete instance and text, children ops) aligned with how `ryact` will drive commits.
- **Incremental updates** on rerender:
  - prop diff and text updates
  - child insert/remove/reorder (keys where tests require)
- Replace “clear and rebuild” commits with correct **reuse** of host nodes where semantics match upstream.

## Milestone 2 — Roots, updates, and scheduling

- **`createRoot` parity:** repeated `render`, unmount, and any strict-mode behavior asserted by translated tests.
- **Batching and lanes** — delegate to `ryact` + `schedulyr` so priorities and flushes match what tests expect.

## Milestone 3 — Events (full incremental parity)

- Capture phase, bubbling, and ordering rules as in upstream tests.
- **Synthetic event** fields and delegation model as asserted (beyond today’s smoke coverage).
- Keep **Pythonic** and **React-style** prop names working (`html_props` or equivalent) without changing JS parity behavior.

## Milestone 4 — Server rendering

- **Serialization parity:** escaping, boolean/void attributes, and attribute name rules to match selected upstream / SSR tests.
- **Streaming or chunked output** only if the parity set requires it; otherwise document as non-goal.
- **Hydration** only if you explicitly expand scope; treat as optional until tests demand it.

---

## “100% parity” (for this package)

- Every **ReactDOM-related** test you track in `tests_upstream/MANIFEST.json` is translated and passing against this renderer + SSR surface.

## Non-goals (unless the manifest moves)

- Real browser DOM or `jsdom`; the default host stays the in-Python model unless you add an adapter.
- npm/React bundles — upstream is referenced for semantics and tests only.
