# Paths to browser JavaScript from Python / PYX (future)

**Today:** the supported way to get a **browser `*.js` bundle** is to author a **JS/TS/JSX/TSX** entry and run **`ryact-build bundle`** (Rolldown). **PYX** and hand-written **Python** components compile to **Python** only (`h` / `create_element`).

**This document** lists the **workstreams and package boundaries** needed if we add a route that **emits client JavaScript** (or TypeScript) from **Python- or PYX-authored** Ryact components—without shipping the CPython runtime (e.g. Pyodide), i.e. a real **compile-to-JS** path.

---

## 1. Source languages and IR

| Source | First step | Notes |
|--------|------------|--------|
| **PYX** | Reuse the existing **PYX AST** (`ryact_pyx`: parse → `ast.py` tree) | Same tree already drives `compile_pyx_to_python`. A second **codegen** could target JS/TS. |
| **Python** (`create_element` / `h` in `.py`) | **Not** defined today | Needs either a **restricted subset** + static analysis, a **macro/DSL** subset, or **“author PYX for the client bundle”** as the supported input for codegen. |

**Decision point:** whether browser emission is **PYX-first** (smallest surface) or includes **arbitrary Python** (much larger).

---

## 2. Package ownership (proposed)

| Package | Responsibility |
|---------|----------------|
| **`ryact-pyx`** | **JS/TS codegen** from the PYX AST (new module alongside existing Python codegen): emit **`jsx()` / `jsxs()`**-style calls, or emit **React/ryact-friendly factory calls**, plus **prop** and **children** mapping. **Golden tests** (PYX file → expected JS snapshot). |
| **`ryact`** | **Semantic contract** the emitter must respect (element shape, keys, `className`, fragments, component boundaries). Document **which** runtime APIs the emitted JS must call (e.g. against a thin **`ryact`** browser entry or upstream-aligned stubs). |
| **`ryact-build`** | **CLI glue**: e.g. `ryact-build pyx-js --input … --out …` (or a flag on **`pyx`**) that writes **`.ts` / `.js`** into the tree; optional **one-shot** “emit + `bundle`” that runs **Rolldown** on a **TS entry** that imports the generated module. **No** change to Rolldown’s role: it still **bundles** authored/generated **JS/TS**. |
| **`ryact-dom` / client** | **Hydration / `createRoot`** contract for code that was **SSR’d from Python** and **hydrated** from **emitted** client code—only if we promise **one** component tree across server and client. |
| **Tests** | **Parity**: same PYX (or fixture) → Python render snapshot vs emitted JS pipeline output (where meaningful). Fuzzing is optional; **golden** files are the minimum. |

---

## 3. Build pipeline shape (target end state)

1. **Input:** `app/Client.pyx` (or future Python subset).
2. **Emit:** `ryact_pyx` (or new package) writes `gen/client.tsx` (or `.js`) that imports from a **defined** `ryact` **browser** public API.
3. **Bundle:** existing **`ryact-build bundle --entry gen/client.tsx --out-dir dist`** (unchanged bundler).
4. **HTML:** existing **`--html` / `--assets`** flow.

Until step 2 exists, **step 3** remains the only path for **JS**: author **`src/main.tsx`** yourself.

---

## 4. Relation to two-lane interop

**Boundary components** (`JsComponentBoundary` / `PyComponentBoundary`) solve **mixing runtimes** at **runtime**. **Emitting JS from PYX** solves **one authoring language → two artifacts** (Python for SSR/tools + JS for the bundle). They can coexist; see [`two_lane_interop_contract.md`](two_lane_interop_contract.md).

---

## 5. Explicit non-paths (unless separately scoped)

- **Pyodide / WASM Python** in the browser — different tradeoff (ship interpreter + Ryact in Python), not “generate JS from components.”
- **Replacing Rolldown** with a Python-only bundler — **non-goal** for `ryact-build` (see `packages/ryact-build/ROADMAP.md`).

---

## 6. Where this is tracked

- **`packages/ryact-build/ROADMAP.md`** — Milestone 2 (**PYX → browser**) points here.
- **`packages/ryact-pyx/README.md`** — short summary + link.

When implementation starts, add **CLI naming**, **versioning**, and **manifest / CI** gates in the **implementing** package’s ROADMAP.
