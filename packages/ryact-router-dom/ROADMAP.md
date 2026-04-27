# ryact-router-dom roadmap

Parity target: **`react-router-dom`** semantics where they make sense for the `ryact` ecosystem.

Constraint: routing spans **core state**, **URL/history integration**, and **host rendering**. Keep the semantic core small and push host-specific integration (DOM vs “native”) to separate layers.

Upstream reference: `react-router` monorepo — `packages/react-router-dom`.

---

## Baseline today (scaffold)

- Package exists and is wired into CI/type paths.
- Placeholder surface for familiar names: `BrowserRouter`, `Routes`, `Route`, `Link`, `use_location`, `use_navigate`, `use_params`.

---

## Milestone 0 — Router core (host-agnostic)

- Define portable core concepts:
  - location model (`pathname`, `search`, `hash`, `state`, `key`)
  - route matching + params extraction
  - navigation API (`navigate(to, replace=False, state=None)`)
- Tests:
  - pure-python unit tests for matching and params

## Milestone 1 — DOM integration layer

- Implement `BrowserRouter`-style history integration for `ryact-dom`.
- Implement `Link` and navigation event wiring.
- Provide a minimal “memory router” for deterministic tests.

## Milestone 2 — Data-router primitives (optional)

- Loader/action style APIs if/when the ecosystem needs them.
- Keep fetch/cache behaviors in separate packages (`ryact-query`).

## Milestone 3 — TSX lane ergonomics

- Ensure router surfaces compile cleanly from TSX→Python (stable import names).
- Add a parity app fixture under `tests_parity/` that exercises routing.

