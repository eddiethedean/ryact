# ryact-build

**Narrow static asset pipeline** for Ryact apps: **`esbuild`** bundles **JS / TS / JSX / TSX** (plus CSS imported from those entries) into an output directory; **`ryact_pyx`** compiles **`.pyx`** into **Python** for the Python lane.

This is **not** a Vite replacement. It is a small Python CLI around the **esbuild binary** for teams that want a **`dist/`-shaped** layout without pulling in Rollup’s full plugin surface.

## Lanes

| Authoring | Output | Tool |
|-----------|--------|------|
| `.ts`, `.tsx`, `.js`, `.jsx` | Browser **JS** (+ **CSS** via `import`) | `esbuild` (Node `npx` or local `node_modules/.bin`) |
| `.pyx` | **Python** (`h` / `create_element`) | `ryact_pyx.compile_pyx_to_python` |

PYX does **not** emit browser JavaScript today. Use **esbuild** for the client bundle and PYX for server-side render, tooling, or hybrid apps that pair Python trees with a small JS shell.

## Prerequisites

- **Node** on `PATH` (`node`, and `npx` unless you install `esbuild` locally).
- In your app project: `npm install -D esbuild` (recommended), or rely on `npx --yes esbuild`. The monorepo root also lists `esbuild` for tests and for `ryact-build bundle` with `--cwd` at the repo root.

## Install (monorepo)

```bash
python -m pip install -e packages/ryact-pyx -e packages/ryact-build
```

(`ryact-build` depends on `ryact-pyx`.)

## CLI

### `bundle` — one-shot `esbuild --bundle`

```bash
ryact-build bundle --entry src/main.tsx --out-dir dist
```

From the **repository root** (using root `node_modules`):

```bash
ryact-build bundle --cwd . --entry packages/ryact-build/tests/fixtures/mini_web/src/entry.ts \
  --out-dir packages/ryact-build/tests/fixtures/mini_web/dist --html packages/ryact-build/tests/fixtures/mini_web/index.html
```

Options (also on `all` and `watch` where applicable):

| Flag | Purpose |
|------|--------|
| `--cwd` | Project root for resolving `node_modules/.bin/esbuild` and relative paths (default: current directory). |
| `--format` | `esm` (default), `iife`, or `cjs`. |
| `--target` | Optional esbuild target, e.g. `es2020`. |
| `--define KEY=VALUE` | Repeatable; passed as `--define:KEY=VALUE` (interop / feature flags). |
| `--inject FILE` | Repeatable; passed as `--inject:FILE` (paths relative to `--cwd` unless absolute). |
| `--html` | **bundle / all:** copy this file into `out-dir` **after** the bundle. **watch:** copy **before** `esbuild --watch` so the dev tree has `index.html` from the first tick. |
| `--assets` | Merge a directory’s top-level children into `out-dir` (same timing as `--html`). |
| `--minify` | Pass `--minify` to esbuild. |
| `--clean` | Delete **contents** of `out-dir` first; only allowed if `out-dir` is a **subdirectory** of `--cwd` (both resolved). |
| `--verbose` | Print the full esbuild argv (shell-quoted) on stderr before running. |
| After `--` | Extra tokens forwarded to esbuild. |

After a successful **bundle** / **all**, if `--html` was copied, **ryact-build** warns on stderr when a **relative** `<script src>` in that HTML does not yet exist under `out-dir` (code-splitting may cause false positives).

### `watch` — `esbuild --bundle --watch`

Same flags as `bundle`. Copies `--html` / `--assets` **once before** starting watch. Blocks until you interrupt the process (Ctrl+C). Does not run HTML script warnings (output appears over time).

### `pyx` — PYX → Python

```bash
ryact-build pyx --input App.pyx --out build/app.py --mode module
```

`--mode` is `module` (default) or `expr`. Warns if `--input` does not end with `.pyx`.

### `all` — PYX then bundle

```bash
ryact-build all --pyx ui/App.pyx --pyx-out build/ui.py --entry src/main.tsx --out-dir dist --html index.html
```

Runs PYX compile first when `--pyx` is set (`--pyx-out` required), then the same pipeline as `bundle`.

## Examples

```bash
# Production-ish bundle with define
ryact-build bundle --entry src/main.tsx --out-dir dist --html index.html --minify \
  --define NODE_ENV=production

ryact-build bundle --entry src/main.tsx --out-dir dist --clean --verbose
```

## Tests

Integration smoke (requires repo `npm install` so `esbuild` exists under the repo root):

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest packages/ryact-build/tests/test_integration_mini_web.py -q
```

## Status

See [ROADMAP.md](ROADMAP.md) for history and future extensions.
