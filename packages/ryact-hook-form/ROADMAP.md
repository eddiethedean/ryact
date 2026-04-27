# ryact-hook-form roadmap

Parity target: **`react-hook-form`** — ergonomic form state management built around hooks.

Goal: keep the package small, predictable, and compatible with both Python-authored and TSX-authored `ryact` apps.

Upstream reference: `react-hook-form/react-hook-form`.

---

## Baseline today (scaffold)

- Package exists and is wired into CI/type paths.
- Placeholder public surface: `use_form()`, `UseFormReturn`, `FormState`.

---

## Milestone 0 — Form state core

- Track:
  - registered fields
  - values + dirty/touched flags
  - submission lifecycle (`is_submitting`, `submit_count`)
- Unit tests for state transitions (no DOM required).

## Milestone 1 — Hook surface + registration API

- `use_form` returns a stable API:
  - `register(name, rules=...)` returning props to spread into inputs (DOM target)
  - `handle_submit(on_valid, on_invalid=None)`
  - `set_value`, `get_values`, `watch`
- Provide an explicit “controller” helper for non-standard inputs.

## Milestone 2 — Validation and resolvers

- Validation modes: onSubmit / onChange / onBlur (minimal)
- Integrations:
  - `ryact-zod` resolver (schema issues → nested error tree)
  - optional `pydantic` resolver for Python-first apps

## Milestone 3 — TSX lane ergonomics

- Ensure register/controller patterns compile cleanly TSX→Python.
- Add a parity app fixture under `tests_parity/` exercising form input + validation.

