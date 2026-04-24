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
from ryact import create_element

el = create_element("div", {"id": "root"}, "hello")
```

## Source of truth

- Upstream: `https://github.com/facebook/react/tree/main/packages/react`

