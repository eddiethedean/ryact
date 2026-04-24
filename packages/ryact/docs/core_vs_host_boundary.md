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

