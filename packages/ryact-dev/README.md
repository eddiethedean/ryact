# ryact-dev

Vite-like dev loop for the `ryact` ecosystem.

Today it covers two loops:

- **TSX → Python**: watch TSX, rebuild via the compiler scripts, restart a Python runner.
- **Pure Python**: watch `.py` / `.css` under a project (optional one-shot build step), then restart your server — no JS bundle.

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

## Example (Python-only app: build static assets + restart server)

From the repo root, after installing `ryact-build` and `ryact-dev` in editable mode:

```bash
ryact-dev python \
  --cwd examples/full_python_ryact \
  --build "python build.py" \
  --run "python serve.py" \
  --persistent-run
```

`build.py` can call `python -m ryact_build.cli static --cwd … --src static --to dist` to merge asset trees; `--run` is any command that starts your HTTP server. Extra paths to watch: `--watch path`. Watches `**/*.py`, `**/*.pyx`, and `**/*.css` under the app working directory.

## Status

Early but useful. The CLI is intentionally small and grows as needs/tests emerge.

