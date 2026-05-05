# ryact-build roadmap

**Goal:** A **small**, **Python-first** build entrypoint for static **HTML/CSS/JS** via **esbuild**, plus **PYX → Python** for the same product’s Python lane.

---

## Baseline (implemented)

- **`bundle`**: esbuild `--bundle` to `--out-dir`, `--platform=browser`, `--sourcemap`; options `--format`, `--target`, `--define`, `--inject`, `--minify`, `--clean`, `--verbose`, passthrough after `--`.
- **`watch`**: same as bundle plus `--watch`; copies `--html` / `--assets` **before** watch.
- **`pyx`**: compile `.pyx` to `.py` via `ryact_pyx`.
- **`all`**: optional PYX step, then same as **`bundle`**.
- Resolve esbuild: `node_modules/.bin/esbuild` / `esbuild.cmd`, else `npx --yes esbuild`.
- **`--clean`**: empty `out-dir` only when it is a strict subdirectory of `--cwd` ([`clean.py`](src/ryact_build/clean.py)).
- **HTML warnings**: after **`bundle`** / **`all`**, optional stderr warnings for missing relative `<script src>` ([`html_check.py`](src/ryact_build/html_check.py)).

---

## Milestone 0 — Ergonomics — **done**

- **`--define` / `--inject`** — forwarded to esbuild (see README).
- **HTML script check** — warn-only after static HTML is copied into `out-dir`.

## Milestone 1 — Watch — **done**

- **`ryact-build watch`** — wraps `esbuild --watch`; static assets copied once before the long-running process.

## Milestone 2 — PYX → browser JS (research)

**Status:** not implemented. PYX and Python lanes emit **Python** only today.

**Cross-repo map** (workstreams, package boundaries, and target pipeline): [`packages/ryact/docs/python_to_browser_js_paths.md`](../ryact/docs/python_to_browser_js_paths.md).

**Rough ownership:**

- **`ryact-pyx`** — JS/TS (or JSX) **codegen** from the existing PYX AST + golden tests.
- **`ryact-build`** — optional **`pyx → file`** CLI step and **“emit then `bundle`”** orchestration; **Rolldown** remains the bundler for any emitted `.ts`/`.js`.
- **`ryact` / `ryact-dom`** — documented **semantic** and **hydration** contracts for emitted client code.

Until that lands, **browser bundles** come only from **TS/JS/JSX/TSX** via **`bundle`** / **`watch`** / **`all`**.

## Non-goals

- Replacing Vite, Rollup, or PostCSS plugin ecosystems.
- Bundling Python for the browser (Pyodide) unless explicitly scoped later.
