# ryact

[![PyPI](https://img.shields.io/pypi/v/ryact.svg)](https://pypi.org/project/ryact/)
[![Python](https://img.shields.io/pypi/pyversions/ryact.svg)](https://pypi.org/project/ryact/)
[![CI](https://github.com/eddiethedean/ryact/actions/workflows/ci.yml/badge.svg)](https://github.com/eddiethedean/ryact/actions/workflows/ci.yml)

Python port of **React core** semantics (parity target: `facebook/react` `packages/react`).

This is intentionally incomplete early on; parity is driven by translated upstream tests in this repo.

## Two-lane developer experience (one semantic core)

The project targets **one semantic core** with **two native authoring lanes**:

- **React developer lane (no Python required)**:
  - Author in **JS/TS + JSX/TSX** using familiar React patterns.
  - An optional toolchain layer (see `packages/ryact/ROADMAP.md`, Milestones 16–19) compiles JSX/TSX down to `ryact` core semantics.
- **Python developer lane (no JavaScript required)**:
  - Author in **Python** using `create_element`/`h` and Pythonic helpers (and optionally PYX).
  - Targets the same `ryact` core semantics and is validated by the same translated tests.

**Constraint:** the lanes must not drift. Behavior changes are either manifest-driven (upstream tests) or optional compilation to existing core semantics.

### Interop contract (mix Python + JS subtrees)

Interop is a first-class goal: mixed-lane apps should be able to mount **JS-authored components inside Python trees** (and Python components inside JSX trees) via explicit boundary nodes and host-level marshalling.

- **User experience / contract**: `packages/ryact/docs/two_lane_interop_contract.md`
- **Roadmap**: see `packages/ryact/ROADMAP.md` Milestone 20
- **Non-goal by default**: “drop in arbitrary npm React components” that require upstream React/ReactDOM

## Parity + translation workflow (ryact monorepo)

- **Manifest gate**: `tests_upstream/MANIFEST.json` contains **implemented-only** translated slices (CI enforces this).
- **React-core upstream inventory**: `tests_upstream/react/upstream_inventory.json` tracks extracted Jest `describe/it/test` cases from upstream `packages/react/src/__tests__` and may include `pending` rows during translation.
- **Drift checks** (run from repo root, requires a local `facebook/react` checkout):

```bash
python scripts/update_react_upstream_inventory.py /path/to/facebook/react
python scripts/check_react_upstream_inventory.py /path/to/facebook/react
```

## Milestone 5 (in progress): Child reconciliation (keys + placement)

The current focus is **keyed child reconciliation** in the deterministic no-op host: insert/move/delete ops, stable identity across reorders, and a small upstream-gated slice.

See:

- `packages/ryact/ROADMAP.md` (Milestone 5 progress)
- `packages/ryact-testkit/src/ryact_testkit/noop_renderer.py` (noop host ops + helpers)
- `tests_upstream/react/test_children_reconciliation.py` (translated tests)
- `tests_upstream/MANIFEST.json` (`react.reconcile.keys.insertMoveDelete`)
- `tests_upstream/react/upstream_inventory.json` (per-case inventory mapping)

## What’s next (Milestones 6+)

Next work remains strictly test-driven. The refined checklists and recommended upstream slices live in `packages/ryact/ROADMAP.md` under:

- Milestone 6 — Class lifecycles + error boundaries
- Milestone 7 — StrictMode + dev-only semantics
- Milestone 8 — Refs, portals, and deeper context semantics

## Install

```bash
pip install ryact
```

## Tiny example (elements)

```python
from ryact import h

el = h("div", {"id": "root"}, "hello")
```

## Pythonic authoring conventions (ergonomics)

- **`h(...)` is a first-class alias** of `create_element(...)`.
- **Children convention**:
  - Prefer positional children: `h("div", None, a, b)`
  - `children=` is supported for programmatic cases; if you pass both positional children and a `children` prop, positional children win.

## Refs (object + callback)

`ryact` supports both object refs (via `create_ref()`) and callback refs (pass a callable as `ref=`).

```python
from ryact import create_element, create_ref

ref = create_ref()
el = create_element("div", {"ref": ref})

def on_ref(value: object | None) -> None:
    ...

el2 = create_element("div", {"ref": on_ref})
```

## Default props (Pythonic)

Prefer expressing defaults using **dataclass defaults** (or `TypedDict` defaults), then pass a constructed props object into `h(...)`/`create_element(...)`. This keeps runtime semantics identical to passing a dict.

## `@component` decorator (optional)

Use `@component` to wrap a function component while keeping its signature/type hints and improving error messages.

```python
from ryact import component, create_element

@component
def App() -> object:
    return create_element("div", {"id": "x"})
```

## Dataclass props (optional)

You can pass a dataclass instance as the `props` argument to `create_element(...)` / `h(...)`.

```python
from dataclasses import dataclass

from ryact import h

@dataclass
class ButtonProps:
    class_name: str = ""
    disabled: bool = False

el = h("button", ButtonProps(class_name="primary", disabled=True), "Save")
```

## Source of truth

- Upstream: `https://github.com/facebook/react/tree/main/packages/react`

