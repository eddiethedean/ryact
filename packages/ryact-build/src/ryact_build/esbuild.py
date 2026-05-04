from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

from .exceptions import EsbuildNotFoundError


def local_esbuild_bin(cwd: Path) -> Path | None:
    """Return `node_modules/.bin/esbuild` (or `esbuild.cmd`) if present."""
    bin_dir = cwd / "node_modules" / ".bin"
    if not bin_dir.is_dir():
        return None
    for name in ("esbuild", "esbuild.cmd"):
        p = bin_dir / name
        if p.is_file():
            return p
    return None


def build_esbuild_argv(cwd: Path, esbuild_args: list[str]) -> list[str]:
    """Build argv to run esbuild; prefer project-local install, else `npx`."""
    local = local_esbuild_bin(cwd)
    if local is not None:
        return [str(local), *esbuild_args]
    npx = shutil.which("npx")
    if npx:
        return [npx, "--yes", "esbuild", *esbuild_args]
    raise EsbuildNotFoundError(
        "Could not find esbuild. Install it in your project (npm install -D esbuild) "
        "or ensure npx is on PATH."
    )


def run_esbuild(esbuild_args: list[str], *, cwd: Path, verbose: bool = False) -> int:
    """Run esbuild in ``cwd``; return process exit code."""
    cmd = build_esbuild_argv(cwd, esbuild_args)
    if verbose:
        print(shlex.join(cmd), file=sys.stderr)
    proc = subprocess.run(cmd, cwd=cwd, env=os.environ)
    return int(proc.returncode)
