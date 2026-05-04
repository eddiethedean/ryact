from __future__ import annotations

import shutil
from pathlib import Path


class UnsafeCleanError(ValueError):
    """Raised when --clean would operate outside the allowed directory tree."""


def clean_out_dir_contents(*, out_dir: Path, cwd: Path) -> None:
    """
    Delete all children of ``out_dir``. Only allowed when ``out_dir`` is a strict
    subdirectory of ``cwd`` (both resolved).
    """
    out_r = out_dir.resolve()
    cwd_r = cwd.resolve()
    if out_r == cwd_r:
        raise UnsafeCleanError("--clean refuses when --out-dir equals --cwd")
    try:
        out_r.relative_to(cwd_r)
    except ValueError as e:
        raise UnsafeCleanError(
            "--clean requires --out-dir to be a subdirectory of --cwd (resolved paths)"
        ) from e

    out_r.mkdir(parents=True, exist_ok=True)
    for child in list(out_r.iterdir()):
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()
