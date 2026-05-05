# ryact-vite

**CLI wrapper around `ryact-build`** (Rolldown in Rust) for the same **HTML + CSS + JS** workflow people associate with “frontend builds”—without **Node.js**, **npm**, or **Vite**.

## What this is (and is not)

- **Is:** A small **Python CLI** that runs **`ryact-build`** (`bundle`, `watch`, `all`, …) from a stable entrypoint, plus **`preview`** via **`python -m http.server`**.
- **Is not:** Vite. There is no Rollup plugin ecosystem, no Vite dev-server/HMR, and no `node_modules/.bin/vite`.

Ryact stays Python-first; **`ryact-vite` is the ergonomic alias** when you want familiar names (`build`, `dev`, `preview`) on top of Rolldown.

## Install

From the monorepo (editable):

```bash
python -m pip install -e packages/ryact-build -e packages/ryact-vite
```

`ryact-vite` declares a dependency on **`ryact-build`**.

## Configuration

Create **`ryact-vite.json`** at your project root (or run `ryact-vite init-config`):

```json
{
  "entry": "src/main.ts",
  "outDir": "dist",
  "html": "index.html",
  "minify": false,
  "clean": false,
  "verbose": false,
  "format": "esm"
}
```

CLI flags override JSON defaults.

## CLI

```bash
ryact-vite build
ryact-vite dev
ryact-vite preview -- --port 8080
```

### `dev` (local URL + watch)

`dev` starts **`ryact-build watch`** (Rolldown rebuilds on save) **and** serves **`outDir`** over HTTP (stdlib `HTTPServer`), default **`http://127.0.0.1:5173/`**.

- **`--port` / `--host`** — override bind (defaults also in `ryact-vite.json` as `devPort`, `devHost`).
- **`--no-livereload`** — disable automatic reload; otherwise, after each **successful** rebuild the browser may reload via a tiny injected `<script src="/__ryact_livereload.js">` (added to your copied HTML when possible).

This is **not** Vite HMR — it is watch + static hosting + optional polling reload.

Forward straight to **`ryact-build`** when you need full control:

```bash
ryact-vite exec bundle --entry src/main.ts --out-dir dist --html index.html
```

Use another directory as the app root:

```bash
ryact-vite --cwd ./apps/web build
```

## Relationship to `ryact-dev`

- **`ryact-dev`**: watch **TSX → Python** and run a Python host.
- **`ryact-vite` / `ryact-build`**: bundle **browser** JS/TS with Rolldown.

Mixed-lane apps can use both. See `packages/ryact/docs/two_lane_interop_contract.md`.

## Migrating from the old Node bridge

Earlier releases spawned **`vite`** via Node. That path is removed. Use **`ryact-vite.json`** + **`ryact-build`** flags instead of `vite.config.*`.

## Status

Thin wrapper over **`ryact-build`**; behavior follows Rolldown and this repo’s bundle pipeline. See `ROADMAP.md` in this directory.
