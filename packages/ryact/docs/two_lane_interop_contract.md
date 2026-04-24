# Two-lane interop contract (user experience)

This document defines the **interop contract** between the two supported authoring lanes:

- **React developer lane**: JS/TS + JSX/TSX authored code compiled to `ryact` core semantics.
- **Python developer lane**: Python (`create_element`/`h`, optionally PYX) authored code targeting the same `ryact` core semantics.

The goal is that teams can **mix lanes in one app** without rewriting everything at once.

---

## Non-negotiable constraint: one semantic core

Both lanes must compile/express UI using the **same semantic core**. Interop is achieved by introducing **explicit boundary elements** that let a host execute a “foreign” subtree and marshal values across the boundary.

Interop must not create a second “almost React” runtime inside the app.

---

## What “interop” means (in-scope)

### Python app uses a JS-authored component

In a Python/PYX project you can mount a JS/JSX component as a subtree:

- The Python tree contains a boundary node like **`JsComponentBoundary`** (name TBD).
- Props/children are marshaled into the JS runtime.
- The JS component returns a `ryact`-compatible element tree (or an intermediate representation) that the host can commit.

### JS/JSX app uses a Python-authored component

In a JS/TSX project (compiled to `ryact` semantics), you can mount a Python component as a subtree:

- The JS tree contains a boundary node like **`PyComponentBoundary`** (name TBD).
- Props/children are marshaled into Python.
- The Python component returns a `ryact.element.Element` subtree.

### Equivalent developer experience expectations

- **Props + children**: cross-boundary behavior must match the same rules as intra-lane usage.
- **Errors**: boundary failures must include a component stack that makes sense in the authoring lane (JSX or Python).
- **Determinism for tests**: `ryact-testkit` must support a deterministic stub for foreign execution so parity tests remain stable.

---

## What is explicitly out-of-scope (until we say otherwise)

### “Drop in arbitrary npm React components”

Using arbitrary npm packages that expect the full upstream **React + ReactDOM** runtime is **not** a goal by default.

Interop targets **components authored for the ryact toolchain** (JS/TSX that compiles to `ryact` semantics), not upstream React runtime execution.

If you later decide to support “real React components” from npm, that becomes a separate milestone because it implies embedding or emulating upstream React/ReactDOM behavior and host integration.

---

## Boundary contract (v0)

### Value marshalling

Across the boundary, values must be marshaled using a conservative, explicit set:

- **Allowed by default**: JSON-serializable values (`None/null`, bool, int/float, str, lists/tuples, dicts with string keys)
- **Special cases**: `Element` trees and children arrays are passed as structured nodes
- **Not allowed by default**: arbitrary host objects, functions/closures, open file handles, etc.

If a host needs to support richer values (e.g. callbacks), it must do so via an explicit adapter layer and tests.

### Refs

- Cross-boundary refs are **not supported by default** until Milestone 8 ref semantics are implemented.

### Effects + scheduling

- Scheduling semantics are owned by the `ryact` core lanes/reconciler.
- Foreign subtrees must not “self-schedule” outside of the host’s lane model.

---

## Where this will live in the codebase (intended)

- **Core** (`packages/ryact`): defines only the semantic primitives and the shape of boundary nodes (if needed).
- **Host/interop** (likely `packages/ryact-dom` and/or a new `packages/ryact-interop`): executes foreign subtrees and performs marshalling.
- **Test harness** (`packages/ryact-testkit`): deterministic stub runners for interop tests.

---

## Milestones that deliver this

See `packages/ryact/ROADMAP.md` under the two-lane developer experience milestones.

