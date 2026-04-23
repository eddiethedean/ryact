# ryact-dom roadmap

Parity target: ReactDOM (`facebook/react` `packages/react-dom`) and (optionally) `react-dom/server`.

## Milestone 0 — Deterministic host + test harness
- Translate a smoke slice of `packages/react-dom/src/__tests__` into `tests_upstream/react_dom/`.
- Ensure `act()` flushes pending work deterministically (scheduler + effects).
- Maintain a stable in-Python DOM host model for assertions.

## Milestone 1 — Host config + mutation model
- Formalize host operations:
  - create instance/text
  - append/insert/remove children
  - update props
  - update text
- Correct diffing behavior on rerender:
  - prop updates
  - text updates
  - child reordering/removal

## Milestone 2 — Roots and lifecycle
- `createRoot` semantics: updates, unmount, strict-mode interactions (as asserted).
- Batching behavior and priority handling via `ryact` + `schedulyr`.

## Milestone 3 — Events (incremental parity)
- Bubble/capture phases, `stopPropagation`, `currentTarget` correctness.
- Event prop mapping rules (e.g., `onClick`) that upstream tests assert on.

## Milestone 4 — Server rendering (if included in parity scope)
- HTML escaping + attribute serialization parity.
- Streaming equivalents (Python-friendly) if tests require.
- Hydration-like semantics only if you choose to implement hydration.

## “100% parity” definition
- All selected upstream ReactDOM tests in `tests_upstream/MANIFEST.json` are translated and passing.

