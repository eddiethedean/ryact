# ryact-zustand roadmap

Parity target (conceptual): **Zustand** — a tiny state store with selector-based subscriptions.

Goal: provide a minimal store API that integrates cleanly with `ryact` hooks and works in both Python and TSX lanes.

Upstream reference: `pmndrs/zustand`.

---

## Baseline today (scaffold)

- Package exists and is wired into CI/type paths.
- Placeholder public surface: `StoreApi`, `create_store`, `use_store`.

---

## Milestone 0 — Store core (no hooks)

- Implement `create_store(initial_state)` returning:
  - `get_state()`
  - `set_state(partial_or_updater, replace=False)`
  - `subscribe(listener)` with `(next, prev)` signature
- Deterministic unit tests for:
  - update ordering
  - replace vs merge semantics
  - subscribe/unsubscribe behavior

## Milestone 1 — Hook integration

- Implement `use_store(store, selector=None)`:
  - default selects entire state
  - selector-based subscriptions with referential equality checks
- Ensure updates schedule correctly under `ryact` lanes/act where relevant.

## Milestone 2 — Middleware patterns (optional)

- `persist`, `devtools`, `subscribeWithSelector` analogs only if tests/apps demand them.

## Milestone 3 — TSX lane ergonomics

- Stable import surface for TSX-authored apps.
- Add a parity app fixture under `tests_parity/` that uses a store + selectors.

