# ryact JSX app (template)

This is a minimal JS/TSX authoring starter that compiles TSX → Python (`h(...)`) and runs it against `ryact-dom`.

## Quickstart

Build `ryact-jsx` once (`cargo build --release --manifest-path packages/ryact-jsx/Cargo.toml`) or set `RYACT_JSX_TO_PY` to the binary. From the repo root:

```bash
python scripts/jsx_build.py templates/ryact_jsx_app/src/main.tsx --out templates/ryact_jsx_app/build/app.py
python templates/ryact_jsx_app/ryact_runner.py
```

Edit `src/main.tsx` and rebuild.

From `templates/ryact_jsx_app/`, you can also run `npm run build` (uses Python; `npm` is not required for the transform).

