# ryact-zod roadmap

Parity target (conceptual): **Zod** — schema-first validation with composable primitives.

Core requirement for the `ryact` ecosystem: schemas must be **portable across lanes**. The canonical artifact is a **language-agnostic AST** (JSON-serializable) plus a stable **issue format**.

Inspiration: `colinhacks/zod`.

---

## Baseline today (implemented)

- Portable AST representation (`Node`), issue format (`Issue`), and `ParseResult`.
- Minimal builder API in Python:
  - `string`, `number`, `boolean`, `literal`, `array`, `union`, `object_`
  - checks: `min_length`, `max_length`, `regex`, `email`
- Validator: `safe_parse(ast, data)` producing canonical issues.

---

## Milestone 0 — Lock the AST contract

- Document the AST schema (kinds + fields) explicitly in this package.
- Add unit tests that assert:
  - stable issue codes/messages
  - stable path semantics (list of keys/indices)
  - stable unknown-keys behavior (`strip`/`passthrough`/`strict`)

## Milestone 1 — Expand primitives + composability

- Add:
  - `optional()` / `nullable()` at the builder level
  - `enum`, `record`, `tuple`, `intersection` (as needed)
  - coercions (carefully: must be lane-consistent)

## Milestone 2 — TSX lane authoring

- Add a tiny TS/JS package (tooling lane) that emits the same AST JSON.
- Teach the TSX→Python compiler to embed or load AST payloads.

## Milestone 3 — Integrations

- `ryact-hook-form` resolver:
  - map issues → nested `errors` tree
- Optional: `pydantic` backend compilation (AST → TypeAdapter/model) for Python apps, while preserving canonical issues.

