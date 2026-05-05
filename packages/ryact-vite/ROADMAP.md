# ryact-vite roadmap

**Goal:** Give web developers a **first-class, familiar `dist/` workflow** while Ryact keeps a **Python semantic core**. This package **wraps `ryact-build` / Rolldown (Rust)**—no Node.js.

---

## Baseline (implemented)

- CLI **`ryact-vite`**: `build` → `ryact-build bundle`, `dev` → `ryact-build watch`, `preview` → `python -m http.server`, `exec` → passthrough to **`ryact-build`**.
- Optional **`ryact-vite.json`** defaults (from **`init-config`**).
- `--cwd` for non-local shell sessions.

---

## Milestone 0 — Preset + docs

- Document a recommended **Ryact + Rolldown** app layout (client `index.html`, `src/main.ts`, optional hybrid interop).
- Optional **shared preset** (resolve aliases, env conventions) published from this package once patterns stabilize.

## Milestone 1 — Monorepo ergonomics

- Root or template script: `create-ryact-app` option that scaffolds **both** `ryact-dev` (TSX→Python lane) and **`ryact-vite`** (browser lane) with one `package.json`.

## Milestone 2 — CI / parity

- Golden or smoke tests that run **`ryact-vite build`** on a tiny fixture and assert `dist/` layout (delegation + exit code).

## Non-goals

- Parity with Vite’s dev-server, HMR, or Rollup plugin ecosystem (use upstream Vite separately if you need that).
- Reimplementing Rolldown in Python (delegation only).
