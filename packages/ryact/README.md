# ryact

[![PyPI](https://img.shields.io/pypi/v/ryact.svg)](https://pypi.org/project/ryact/)
[![Python](https://img.shields.io/pypi/pyversions/ryact.svg)](https://pypi.org/project/ryact/)
[![CI](https://github.com/eddiethedean/ryact/actions/workflows/ci.yml/badge.svg)](https://github.com/eddiethedean/ryact/actions/workflows/ci.yml)

Python port of **React core** semantics (parity target: `facebook/react` `packages/react`).

This is intentionally incomplete early on; parity is driven by translated upstream tests in this repo.

## Parity + translation workflow (ryact monorepo)

- **Manifest gate**: `tests_upstream/MANIFEST.json` contains **implemented-only** translated slices (CI enforces this).
- **React-core upstream inventory**: `tests_upstream/react/upstream_inventory.json` tracks extracted Jest `describe/it/test` cases from upstream `packages/react/src/__tests__` and may include `pending` rows during translation.
- **Drift checks** (run from repo root, requires a local `facebook/react` checkout):

```bash
python scripts/update_react_upstream_inventory.py /path/to/facebook/react
python scripts/check_react_upstream_inventory.py /path/to/facebook/react
```

## Milestone 1 (in progress): Elements identity hardening

The current focus is `create_element` / `Element` semantics driven by upstream `ReactCreateElement-test.js`. See:

- `packages/ryact/ROADMAP.md` (Milestone 1 progress)
- `tests_upstream/react/test_create_element.py` (translated tests)
- `tests_upstream/react/upstream_inventory.json` (per-case inventory mapping)

## What’s next (Milestones 2–4)

Milestones 2+ are hooks/reconciler/concurrency work that should remain strictly test-driven. The refined checklists and recommended upstream slices live in `packages/ryact/ROADMAP.md` under:

- Milestone 2 — Hooks parity
- Milestone 3 — Reconciler (“fiber-like”) correctness
- Milestone 4 — Concurrency + Suspense

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

