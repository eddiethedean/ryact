# ryact

[![CI](https://github.com/eddiethedean/ryact/actions/workflows/ci.yml/badge.svg)](https://github.com/eddiethedean/ryact/actions/workflows/ci.yml)

Python ports of **React**, **ReactDOM**, **Scheduler**, and a **React Native–style renderer**, with behavior driven by translated upstream tests.

## Packages

- `schedulyr`: Scheduler port (`facebook/react` `packages/scheduler`)
- `ryact`: React core port (`facebook/react` `packages/react`)
- `ryact-dom`: ReactDOM-style renderer + server-render placeholder (`facebook/react` `packages/react-dom`)
- `ryact-native`: native renderer scaffold
- `ryact-testkit`: shared test harness for translated upstream tests

## Parity strategy

- **Source of truth**: `facebook/react` (upstream semantics + tests)
- **Primary gate**: pytest translations under `tests_upstream/`
- **Manifest gate**: `tests_upstream/MANIFEST.json` must only contain implemented tests (CI enforces this)
- **Scheduler upstream checklist**: `tests_upstream/scheduler/upstream_inventory.json` lists every Jest case under `packages/scheduler/src/__tests__`; CI runs `scripts/check_scheduler_upstream_inventory.py` against a shallow `facebook/react` clone. Regenerate with `.venv/bin/python scripts/update_scheduler_upstream_inventory.py /path/to/react` (or activate `.venv` first and use `python`).

## Quickstart (local dev)

Use a **project-local virtualenv** at **`.venv`** (same layout as CI’s Python 3.11):

```bash
python3.11 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
python -m pip install -U pip
python -m pip install -e packages/schedulyr -e packages/ryact -e packages/ryact-dom -e packages/ryact-native -e packages/ryact-testkit
python -m pip install -U ruff ty pytest
```

With `.venv` activated, run the translated test suite:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest
```

Format and lint:

```bash
ruff format .
ruff check .
```

Typecheck:

```bash
ty check .
```

Without activating the venv, prefix commands with **`.venv/bin/`** (e.g. `.venv/bin/pytest`, `.venv/bin/ruff check .`).

## Upstream references

- `https://github.com/facebook/react`
- `https://github.com/facebook/react/tree/main/packages/react`
- `https://github.com/facebook/react/tree/main/packages/react-dom`
- `https://github.com/facebook/react/tree/main/packages/scheduler`

