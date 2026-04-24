# ryact JSX app (template)

This is a minimal JS/TSX authoring starter that compiles TSX → Python (`h(...)`) and runs it against `ryact-dom`.

## Quickstart

From the repo root:

```bash
npm install
node scripts/jsx_build.mjs templates/ryact_jsx_app/src/main.tsx --out templates/ryact_jsx_app/build/app.py
python templates/ryact_jsx_app/ryact_runner.py
```

Edit `src/main.tsx` and rebuild.

