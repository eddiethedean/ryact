# ryact-query roadmap

Parity target: **`@tanstack/react-query`** (package: `react-query`) where it can be represented in the `ryact` runtime.

Goal: a small, test-driven query cache with a stable hook surface for apps and for future router/data integrations.

Upstream reference: [`TanStack/query` `packages/react-query`](https://github.com/TanStack/query/tree/main/packages/react-query)

---

## Baseline today (scaffold)

- Package exists and is wired into CI/type paths.
- Placeholder public surface: `QueryClient`, `QueryKey`, `QueryResult`, `use_query`.

---

## Milestone 0 — Query cache core (no hooks)

- `QueryClient` with:
  - normalized query keys
  - cache entry states: idle/loading/success/error
  - observers/subscribers per key
- Deterministic unit tests for cache transitions.

## Milestone 1 — Hook surface for `ryact`

- `use_query` basic behavior:
  - `enabled`, `initial_data`
  - loading → success/error
  - refetch triggers (manual, dependency changes)
- Error + loading semantics are driven by parity tests we add in this repo (not upstream Jest directly).

## Milestone 2 — Scheduling + cancellation integration

- Integrate with `ryact` scheduling:
  - cooperative updates (lanes / transition) where relevant
  - cancellation signals (`ryact.cache_signal`) as a transport-agnostic abort primitive

## Milestone 3 — Ecosystem integration

- Router loaders (if added) can use `ryact-query` for caching.
- `ryact-hook-form` can use `ryact-query` for async validation where needed.

