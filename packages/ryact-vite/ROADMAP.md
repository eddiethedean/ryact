# ryact-vite roadmap

**Goal:** Give React web developers a **first-class, familiar `dist/` workflow** while Ryact keeps a **Python semantic core**. This package **orchestrates Vite** (Node); it does not replace Vite’s implementation.

---

## Baseline (implemented)

- CLI **`ryact-vite`** with `dev`, `build`, `preview`, and `exec` (arbitrary Vite subcommand).
- Resolve Vite via `node_modules/.bin/vite` (or `vite.cmd` on Windows), else `npx --yes vite`.
- Optional `init-config` to copy a minimal `vite.config.ryact.mjs` into the cwd.
- `--cwd` for non-local shell sessions.

---

## Milestone 0 — Preset + docs

- Document a recommended **Ryact + Vite** app layout (client `index.html`, `src/main.tsx` using upstream React, or hybrid interop).
- Optional **shared preset** (resolve aliases, env conventions) published from this package once patterns stabilize.

## Milestone 1 — Monorepo ergonomics

- Root or template script: `create-ryact-app` option that scaffolds **both** `ryact-dev` (TSX→Python lane) and **`ryact-vite`** (browser lane) with one `package.json`.

## Milestone 2 — CI / parity

- Golden or smoke tests that run `vite build` on a tiny fixture and assert `dist/` layout (no need to port Vite; assert delegation + exit code).

## Non-goals

- Reimplementing Rollup, esbuild, or Vite plugins in Python.
- Replacing Node for production bundling of npm packages.
