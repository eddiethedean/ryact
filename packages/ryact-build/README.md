# ryact-build

**Narrow static asset pipeline** for Ryact apps: the **[Rolldown](https://github.com/rolldown/rolldown)** bundler (Rust), exposed via a **PyO3** native extension, bundles **JS / TS / JSX / TSX** (plus CSS imported from entries) into an output directory; **`ryact_pyx`** compiles **`.pyx`** into **Python** for the Python lane.

This is **not** a Vite replacement. It is a small Python CLI for a **`dist/`-shaped** layout without pulling in Rollup’s full plugin surface.

## Lanes

| Authoring | Output | Tool |
|-----------|--------|------|
| `.ts`, `.tsx`, `.js`, `.jsx` | Browser **JS** (+ **CSS** via `import`) | Rolldown (`ryact_build._native`) |
| `.pyx` | **Python** (`h` / `create_element`) | `ryact_pyx.compile_pyx_to_python` |

PYX does **not** emit browser JavaScript today. Use **ryact-build** for the client bundle and PYX for server-side render, tooling, or hybrid apps.

**Future (planned workstreams only):** [`packages/ryact/docs/python_to_browser_js_paths.md`](../ryact/docs/python_to_browser_js_paths.md) — how **`ryact-pyx`**, **`ryact-build`**, and the **`ryact`** core could split responsibility for a **PYX → JS/TS → Rolldown** pipeline.

## Prerequisites

- **Rust** toolchain **1.93.1+** (see [`rust-toolchain.toml`](rust-toolchain.toml)) to compile the extension.
- **Python 3.8+**.
- **No Node.js** is required for bundling (fixtures that only use plain TS/JS work without `npm install`).

Editable installs compile the native module via **[maturin](https://www.maturin.rs/)** (`pip` pulls the build backend from `pyproject.toml`).

From `packages/ryact-build`:

```bash
rustup show   # ensure 1.93.1+ active, or rely on rust-toolchain.toml
python -m pip install maturin
maturin develop
```

Or install the package in editable mode from the repo root (same build):

```bash
python -m pip install -e packages/ryact-pyx -e packages/ryact-build
```

(`ryact-build` depends on `ryact-pyx`.)

## CLI

### `bundle` — one-shot bundle

```bash
ryact-build bundle --entry src/main.tsx --out-dir dist
```

From the **repository root**:

```bash
ryact-build bundle --cwd . --entry packages/ryact-build/tests/fixtures/mini_web/src/entry.ts \
  --out-dir packages/ryact-build/tests/fixtures/mini_web/dist --html packages/ryact-build/tests/fixtures/mini_web/index.html
```

Options (also on `all` and `watch` where applicable):

| Flag | Purpose |
|------|--------|
| `--cwd` | Project root for resolving relative paths (default: current directory). |
| `--format` | `esm` (default), `iife`, or `cjs`. |
| `--target` | Reserved; not wired to Rolldown in this release (warning only). |
| `--define KEY=VALUE` | Repeatable compile-time defines. |
| `--inject FILE` | Not implemented yet for Rolldown (warning only). |
| `--html` | **bundle / all:** copy into `out-dir` **after** the bundle. **watch:** copy **before** the watcher starts. |
| `--assets` | Merge a directory’s top-level children into `out-dir` (same timing as `--html`). |
| `--minify` | Enable minification in Rolldown. |
| `--clean` | Delete **contents** of `out-dir` first; only if `out-dir` is a **subdirectory** of `--cwd` (both resolved). |
| `--verbose` | Print Rolldown options / paths on stderr. |

After a successful **bundle** / **all**, if `--html` was copied, **ryact-build** warns on stderr when a **relative** `<script src>` in that HTML does not yet exist under `out-dir` (code-splitting may cause false positives).

### `watch` — rebuild on file changes

Same flags as `bundle`. Copies `--html` / `--assets` **once before** starting the file watcher (watchdog). Blocks until Ctrl+C. Does not run HTML script warnings on every rebuild.

### `pyx` — PYX → Python

```bash
ryact-build pyx --input App.pyx --out build/app.py --mode module
```

### `all` — PYX then bundle

```bash
ryact-build all --pyx ui/App.pyx --pyx-out build/ui.py --entry src/main.tsx --out-dir dist --html index.html
```

## Rolldown version

The Rust crate is pinned to a **git revision** of `rolldown` (see [`Cargo.toml`](Cargo.toml)). Bump the `rev` when you intentionally upgrade the bundler.

## Tests

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest packages/ryact-build/tests -q
```

## Status

See [ROADMAP.md](ROADMAP.md) for history and future extensions.
