#!/usr/bin/env python3
"""Compile ``app/page.pyx`` → ``app/page_gen.py``, then merge ``static/`` into ``dist/``."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parent
    pyx = subprocess.call(
        [
            sys.executable,
            "-m",
            "ryact_build.cli",
            "pyx",
            "--input",
            str(root / "app" / "page.pyx"),
            "--out",
            str(root / "app" / "page_gen.py"),
            "--mode",
            "module",
        ]
    )
    if pyx != 0:
        return pyx
    return int(
        subprocess.call(
            [
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
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
