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

## Milestone 2 — PYX → browser (research)

- Only if a **stable** compile target to JS exists; likely **out of scope** for this package and belongs in `ryact-pyx` or a dedicated compiler.

## Non-goals

- Replacing Vite, Rollup, or PostCSS plugin ecosystems.
- Bundling Python for the browser (Pyodide) unless explicitly scoped later.
