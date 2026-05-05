from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

Format = Literal["esm", "iife", "cjs"]


@dataclass(frozen=True)
class BundleConfig:
    """Arguments for a single Rolldown bundle (or watch) run."""

    entry: Path
    out_dir: Path
    minify: bool = False
    format: Format = "esm"
    target: str | None = None
    defines: tuple[tuple[str, str], ...] = ()
    injects: tuple[Path, ...] = ()
    watch: bool = False


def parse_define_arg(raw: str) -> tuple[str, str]:
    """Parse ``KEY=VALUE`` for ``--define``."""
    if "=" not in raw:
        raise ValueError(f"expected KEY=VALUE, got {raw!r}")
    key, _, val = raw.partition("=")
    if not key:
        raise ValueError(f"expected KEY=VALUE, got {raw!r}")
    return key, val
