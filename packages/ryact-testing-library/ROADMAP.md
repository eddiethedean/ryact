# ryact-testing-library roadmap

Parity target (conceptual): **React Testing Library** ergonomics for `ryact` apps.

Goal: accelerate parity work and app authoring by providing a tiny, stable layer for:
- rendering
- querying
- events
- async waiting

Inspiration: `testing-library/react-testing-library`.

---

## Baseline today (scaffold)

- Package exists and is wired into CI/type paths.
- Placeholder API surface will be grown test-first.

---

## Milestone 0 — Render + debug

- `render(element)` returning a handle with:
  - `container` (DOM container / noop container)
  - `debug()` dumps deterministic output
- Basic text queries:
  - `get_by_text`, `query_by_text`

## Milestone 1 — Events

- `fire_event.click`, `fire_event.input/change` for `ryact-dom`
- Host-agnostic event intent (DOM mapping can live in `ryact-dom` integration)

## Milestone 2 — Async helpers

- `wait_for(fn, timeout_ms=..., interval_ms=...)`
- `find_by_*` queries built on `wait_for`

## Milestone 3 — Integration surfaces

- Act integration: always run updates inside `ryact-testkit.act()` when applicable
- `ryact-dev` workflows: snapshot diffs and watch-friendly output

