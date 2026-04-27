# ryact-dev roadmap

Parity target (conceptual): **Vite-like dev loop** for the `ryact` ecosystem — fast rebuilds, watch mode, and an ergonomic feedback loop for the TSX→Python lane.

This package is **not** manifest-gated by upstream React tests. Instead, it should stay:
- **Small** (thin wrapper around existing repo scripts)
- **Deterministic** (predictable logs/exit codes)
- **Composable** (can be used by templates and parity apps)

---

## Baseline today (implemented)

- CLI: **`ryact-dev`**
  - `jsx`: watch TSX/JSX, compile via `scripts/jsx_build.mjs`, then run a Python command
  - `test`: watch files and rerun pytest (supports `--default-env` for `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`)

---

## Milestone 0 — Stabilize “JSX lane dev loop”

- Better error surfaces:
  - show TSX source locations when compilation fails
  - show the command that ran and preserve exit codes
- Watch ergonomics:
  - configurable ignore/include patterns
  - explicit debounce/aggregation rules

## Milestone 1 — Long-running runner integration

- Support “server-style” Python runners:
  - persistent subprocess with restart on rebuild (already supported)
  - optional “graceful” shutdown hooks (SIGINT/SIGTERM behavior documented)

## Milestone 2 — TSX template workflow

- First-class template experience:
  - `ryact-dev jsx templates/ryact_jsx_app/...` becomes the documented happy path
  - optional `ryact-dev init` wrapper around `scripts/create_ryact_app.py`

## Milestone 3 — Parity-app support

- Add utilities to run `tests_parity/` “apps” in watch mode
- Optional: snapshot diff printing for `ryact-dom` container output

