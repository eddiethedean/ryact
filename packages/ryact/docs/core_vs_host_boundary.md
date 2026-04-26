## Core vs host boundary (source of truth)

`ryact` is the semantic core (React-ish element model, hooks, reconciler), while host packages (e.g. `ryact-dom`, `ryact-native`) implement environment-specific behavior like host instances, event systems, and serialization.

### Test suite ownership

- `tests_upstream/react/*`: core semantics
  - Elements (`create_element`), component model, hooks, reconciler behavior.
  - No-op host behavior used for determinism in tests (not a production host).
- `tests_upstream/react_dom/*`: DOM host semantics
  - Roots (`create_root`), portals, attribute/prop normalization, events, SSR surfaces.
- `tests_upstream/scheduler/*`: `schedulyr` parity

### Where to translate an upstream test

- If the upstream test imports/assumes DOM APIs or serialization (`react-dom`, attribute rules, hydration warnings, event replay), it belongs under `react_dom`.
- If the upstream test asserts semantics that should hold across hosts (hook rules, update ordering, key reconciliation invariants), it belongs under `react`.

### SSR + hydration policy

SSR/hydration work only lands when it is **manifest-gated** (added to `tests_upstream/MANIFEST.json` via translated upstream slices). Hydration is explicitly out of scope unless the manifest expands to include it.

### `react_dom` upstream inventory: `pending` vs `non_goal`

[`tests_upstream/react_dom/upstream_inventory.json`](../../tests_upstream/react_dom/upstream_inventory.json) tracks every extracted upstream `it(...)` from `packages/react-dom`.

- **`pending`**: honest backlog — we have not decided scope yet, or we intend to translate/implement it later.
- **`implemented`**: must reference a real `manifest_id` in [`tests_upstream/MANIFEST.json`](../../tests_upstream/MANIFEST.json) and a concrete `python_test` module (enforced by schema tests).
- **`non_goal`**: explicitly out of scope for the current in-Python DOM host / SSR subset. Every `non_goal` row **must** include a non-empty `non_goal_rationale` (schema-enforced). Prefer this over leaving rows `pending` indefinitely when the upstream case assumes a browser engine, full event/compositor behavior, or other environments we do not model.

When closing out a large upstream file in waves, prefer **small translated slices** (`implemented`) plus either remaining `pending` (backlog) or narrowly-scoped `non_goal` rationales — avoid mixing meanings (do not mark `non_goal` for work you still plan to treat as parity).

