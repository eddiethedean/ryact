# Benchmarks (optional)

These benchmarks are **not** part of the default CI gate. They exist for local regression
tracking and optional manual CI runs.

## Setup

From the repo root (with your `.venv` activated, or prefix with `.venv/bin/`):

```bash
python -m pip install pyperf
python benchmarks/run_scheduler_bench.py --n 20000 -o bench.json
python -m pyperf stats bench.json
```

## Notes

- Results vary by machine and system load; treat this as **regression detection**, not an
  absolute performance claim.
- For more stable results, see `python -m pyperf system tune` (requires elevated permissions
  on some systems).

