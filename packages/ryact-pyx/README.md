# ryact-pyx

Optional **PYX** (XML-like) authoring layer for `ryact`.

This package compiles PYX source into Python code that calls `ryact.h(...)` / `ryact.create_element(...)`.

## Status

Early, manifest-independent ergonomics tooling. The compiler is intentionally separate from `ryact` runtime semantics.

## Path to browser JavaScript (not implemented)

PYX currently compiles **only to Python** (`h` / `create_element`). There is **no** emitter to JS/TS yet.

If we add one, the planned **package boundaries, pipeline shape, and non-goals** are documented in **`packages/ryact/docs/python_to_browser_js_paths.md`** (see also **`packages/ryact-build/ROADMAP.md`** — Milestone 2).

**Until then:** ship client **`*.js`** with **`ryact-build bundle`** on a **JS/TS/JSX/TSX** entry; use PYX/Python for **SSR**, tooling, or **hybrid** apps.

