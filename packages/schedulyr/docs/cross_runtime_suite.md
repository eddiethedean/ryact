## Cross-runtime parity suite (optional)

This suite records a curated set of scheduler scenarios from:
- **Python** (`schedulyr` harnesses)
- **Upstream React** (local `facebook/react` checkout)

…and compares event logs per scenario.

### Python record

```bash
.venv/bin/python scripts/scheduler_node_crosscheck.py python-record --out artifacts/scheduler_crosscheck_python.json
```

### Upstream record

```bash
.venv/bin/python scripts/scheduler_node_crosscheck.py upstream-record --react-path /path/to/react --out artifacts/scheduler_crosscheck_upstream.json
```

### Cross-compare

```bash
.venv/bin/python scripts/scheduler_node_crosscheck.py cross-compare --python-json artifacts/scheduler_crosscheck_python.json --upstream-json artifacts/scheduler_crosscheck_upstream.json
```

If the compare fails, `cross-compare` writes a JSON diff artifact (default path shown by the command help).

### Notes
- The upstream recorder uses React’s Jest transformer, so the upstream checkout must have deps installed (`yarn install` is typical).
- Scenarios are designed to be deterministic (virtual time + mock hosts). Avoid adding wall-clock timing or environment-dependent logs.

