from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from .exceptions import ViteNotFoundError


def local_vite_bin(cwd: Path) -> Path | None:
    """Return `node_modules/.bin/vite` (or `vite.cmd`) if present."""
    bin_dir = cwd / "node_modules" / ".bin"
    if not bin_dir.is_dir():
        return None
    for name in ("vite", "vite.cmd"):
        p = bin_dir / name
        if p.is_file():
            return p
    return None


def build_vite_argv(cwd: Path, vite_args: list[str]) -> list[str]:
    """Build argv to run Vite; prefer project-local install, else `npx`."""
    local = local_vite_bin(cwd)
    if local is not None:
        return [str(local), *vite_args]
    npx = shutil.which("npx")
    if npx:
        return [npx, "--yes", "vite", *vite_args]
    raise ViteNotFoundError(
        "Could not find Vite. Install it in your project (npm install -D vite) "
        "or ensure npx is on PATH."
    )


def run_vite(vite_args: list[str], *, cwd: Path) -> int:
    """Run Vite in ``cwd``; forward exit code."""
    cmd = build_vite_argv(cwd, vite_args)
    proc = subprocess.run(cmd, cwd=cwd, env=os.environ)
    return int(proc.returncode)
