#!/usr/bin/env python3
"""Copy static assets into dist/ via ``ryact-build static`` (no JS bundle)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parent
    cmd = [
        sys.executable,
        "-m",
        "ryact_build.cli",
        "static",
        "--cwd",
        str(root),
        "--src",
        "static",
        "--to",
        "dist",
    ]
    return int(subprocess.call(cmd))


if __name__ == "__main__":
    raise SystemExit(main())
