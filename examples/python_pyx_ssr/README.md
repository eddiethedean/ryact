# Python + PYX + ryact-dom (no JavaScript)

Author the UI in **`app/page.pyx`** (XML-like syntax). **`ryact-build pyx`** compiles it to **`app/page_gen.py`** (`def render(scope: dict[str, object])` using `ryact.h`). **`ryact-build static`** copies **`static/`** into **`dist/`** for the server.

## One-time setup (from repo root)

```bash
python -m pip install -e packages/ryact -e packages/ryact-pyx -e packages/ryact-dom -e packages/ryact-build -e packages/ryact-dev
```

## Build

```bash
python examples/python_pyx_ssr/build.py
```

## Run

```bash
cd examples/python_pyx_ssr
python serve.py
```

Open **http://127.0.0.1:8766/** (this example defaults to **8766** so it can run beside `full_python_ryact` on 8765). Override with `--port` or `RYACT_PORT`.

## Dev loop (watch `.py` / `.pyx` / `.css`, rebuild, restart)

From **repo root**:

```bash
ryact-dev python \
  --cwd examples/python_pyx_ssr \
  --build "python build.py" \
  --run "python serve.py" \
  --persistent-run
```

## Notes

- **Sibling keys:** In development, Ryact warns if a host node has multiple element children without `key`. This example sets `key` on multi-child nodes in PYX where needed.
- PYX does **not** emit browser JavaScript; **`ryact-build bundle`** is for JS/TS entries. This app is **SSR-only** with the stdlib HTTP server.
- **Roadmap for PYX → JS / hybrid bundles:** [`packages/ryact/docs/python_to_browser_js_paths.md`](../../packages/ryact/docs/python_to_browser_js_paths.md).
