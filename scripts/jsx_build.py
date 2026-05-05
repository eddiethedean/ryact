#!/usr/bin/env python3
"""Compile TSX to a Python module using `ryact-jsx` (same contract as legacy `jsx_build.mjs`)."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    # Import after path setup for `python scripts/jsx_build.py` without editable install.
    sys.path.insert(0, str(_REPO_ROOT))
    from scripts.jsx_to_py import jsx_to_python

    parser = argparse.ArgumentParser(description="Compile TSX to Python module (ryact-jsx).")
    parser.add_argument("input", type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--map", type=Path, default=None)
    args = parser.parse_args()

    result = jsx_to_python(path=args.input.resolve(), mode="module")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(result.code, encoding="utf8")

    if args.map:
        m = re.search(r"__ryact_jsx_map__\s*=\s*(\[[\s\S]*?\])\n\ndef render", result.code)
        mappings = json.loads(m.group(1)) if m else []
        payload = {
            "input": str(args.input),
            "generated": str(args.out),
            "version": 0,
            "mappings": mappings,
        }
        args.map.parent.mkdir(parents=True, exist_ok=True)
        args.map.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
