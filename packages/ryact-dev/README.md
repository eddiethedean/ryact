# ryact-dev

Vite-like dev loop for the `ryact` ecosystem.

Today, it focuses on the repo’s **TSX → Python** lane: watch TSX files, rebuild via the existing compiler scripts, then restart a Python runner (e.g. `ryact-dom` runner) with readable errors.

## Install (editable, from repo root)

```bash
pip install -e packages/ryact-dev
```

## Example (template app)

From the repo root:

```bash
npm install
ryact-dev jsx templates/ryact_jsx_app/src/main.tsx --out templates/ryact_jsx_app/build/app.py --run "python templates/ryact_jsx_app/ryact_runner.py" --persistent-run
```

## Example (watch tests)

```bash
ryact-dev test --default-env
```

## Status

Early but useful. The CLI is intentionally small and grows as needs/tests emerge.

