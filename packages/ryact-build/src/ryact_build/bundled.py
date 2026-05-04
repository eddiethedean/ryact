"""Locate an esbuild executable shipped inside the ``ryact-build`` wheel (optional)."""

from __future__ import annotations

import sys
from pathlib import Path


def bundled_esbuild_binary() -> Path | None:
    """
    Return the path to the platform binary extracted under ``ryact_build/_bundled/``,
    or ``None`` if this install was built without vendoring (e.g. editable checkout).
    """
    base = Path(__file__).resolve().parent / "_bundled"
    name = "esbuild.exe" if sys.platform == "win32" else "esbuild"
    p = base / name
    if p.is_file():
        return p
    return None
