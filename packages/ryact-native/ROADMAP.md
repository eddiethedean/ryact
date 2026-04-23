# ryact-native roadmap

Parity target: React Native–style host renderer semantics.

## Milestone 0 — Define “source of truth” + harness
- Choose and lock a specific upstream reference for tests/behavior (e.g. RN repo tests or a curated subset).
- Build a deterministic in-memory native host model suitable for assertions.
- Add a native section to `tests_upstream/MANIFEST.json`.

## Milestone 1 — Host config + mutations
- Formalize native host operations (create view/text, insert/remove, update props).
- Correct diffing behavior for rerenders:
  - prop updates
  - text updates
  - child reordering/removal

## Milestone 2 — Updates + scheduling integration
- Priority handling and yielding via `ryact` + `schedulyr`.
- `act()` flush integration for deterministic tests.

## Milestone 3 — Platform behaviors (only as tests require)
- Event/gesture abstractions.
- Layout measurement hooks or platform-specific props.

## “100% parity” definition
- All native tests selected in `tests_upstream/MANIFEST.json` are translated and passing for the chosen upstream reference.

