# Full Python Ryact example (no JavaScript)

This app uses **only** `ryact`, **ryact-dom** (`render_to_string`), and the stdlib HTTP server. There is **no** TypeScript/JavaScript bundle.

## One-time setup (from repo root)

```bash
python -m pip install -e packages/ryact -e packages/ryact-dom -e packages/ryact-build -e packages/ryact-dev
```

## Build (static assets → `dist/`)

```bash
python -m ryact_build.cli static \
  --cwd examples/full_python_ryact \
  --src static \
  --to dist
```

Or:

```bash
python examples/full_python_ryact/build.py
```

## Run the server

```bash
cd examples/full_python_ryact
python serve.py
```

Open **http://127.0.0.1:8765/** (override with `--port` or `RYACT_PORT`).

## Dev loop (watch Python/CSS, rebuild static, restart server)

From **repo root**:

```bash
ryact-dev python \
  --cwd examples/full_python_ryact \
  --build "python build.py" \
  --run "python serve.py" \
  --persistent-run
```

Edit `app/ui.py`, `serve.py`, or `static/*` — on save, `build.py` runs (copies CSS into `dist/static/`) and `serve.py` restarts.

## Notes

- **SSR only** here: each GET `/` re-renders the tree. For interactive Python UI in-process, you’d use `create_root` + `Container` (see `ryact-dom` README) instead of string output.
- **`ryact-build bundle`** is for JS/TS entries; this example uses **`ryact-build static`** for assets only.
