# ryact-vite

**Bridge to [Vite](https://vitejs.dev/)** for Ryact projects that need the same **HTML + CSS + JS** artifacts React developers get from `vite build` (a `dist/` tree for static hosts and CDNs).

## What this is (and is not)

- **Is:** A small **Python CLI** that runs the **real Vite** from your app’s `node_modules` (or via `npx`) so you do not re-learn tooling when shipping browser bundles.
- **Is not:** A line-by-line rewrite of Vite in Python. Vite depends on esbuild, Rollup, and a large plugin ecosystem; this package **delegates** to Node for that surface.

Ryact’s core remains Python-first; **`ryact-vite` is the supported path when the product is a classic web build** (entry HTML, hashed assets, `preview`).

## Install

From the monorepo (editable):

```bash
python -m pip install -e packages/ryact-vite
```

In your **web app** directory (alongside `package.json`):

```bash
npm install -D vite
```

## CLI

From your Vite project root (where `vite.config.*` and `node_modules` live):

```bash
ryact-vite dev
ryact-vite build
ryact-vite preview
```

Forward extra args to Vite:

```bash
ryact-vite dev -- --port 5174
ryact-vite build -- --emptyOutDir
```

Use another directory as the app root:

```bash
ryact-vite --cwd ./apps/web dev
```

Drop a starter config into the current directory:

```bash
ryact-vite init-config
```

That writes `vite.config.ryact.mjs` (minimal `defineConfig`); rename or merge into your own `vite.config.ts` as needed.

## Relationship to `ryact-dev`

- **`ryact-dev`**: watch **TSX → Python** and run a Python host (semantic core in-process).
- **`ryact-vite`**: run **Vite** for **browser** bundles and static `dist/` output.

Mixed-lane apps can use both: e.g. Python/ryact for SSR or tooling, Vite for the client bundle. See `packages/ryact/docs/two_lane_interop_contract.md` and `ROADMAP.md` in this directory.

## Status

Early bridge; behavior is “whatever Vite does,” with stable invocation from Python. See `ROADMAP.md` for planned presets and repo integration.
