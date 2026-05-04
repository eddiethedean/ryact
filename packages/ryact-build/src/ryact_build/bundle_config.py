from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

Format = Literal["esm", "iife", "cjs"]


@dataclass(frozen=True)
class BundleConfig:
    """Arguments for a single esbuild bundle (or watch) invocation."""

    entry: Path
    out_dir: Path
    minify: bool = False
    format: Format = "esm"
    target: str | None = None
    defines: tuple[tuple[str, str], ...] = ()
    injects: tuple[Path, ...] = ()
    extra: tuple[str, ...] = ()
    watch: bool = False


def bundle_argv(config: BundleConfig) -> list[str]:
    """Build esbuild CLI argv from config (entry first, stable define order)."""
    parts: list[str] = [
        str(config.entry),
        "--bundle",
        f"--outdir={config.out_dir}",
        f"--format={config.format}",
        "--platform=browser",
        "--sourcemap",
    ]
    if config.target:
        parts.append(f"--target={config.target}")
    if config.minify:
        parts.append("--minify")
    for key, val in sorted(config.defines, key=lambda kv: kv[0]):
        parts.append(f"--define:{key}={val}")
    for inj in config.injects:
        parts.append(f"--inject:{inj}")
    parts.extend(config.extra)
    if config.watch:
        parts.append("--watch")
    return parts


def parse_define_arg(raw: str) -> tuple[str, str]:
    """Parse ``KEY=VALUE`` for ``--define``."""
    if "=" not in raw:
        raise ValueError(f"expected KEY=VALUE, got {raw!r}")
    key, _, val = raw.partition("=")
    if not key:
        raise ValueError(f"expected KEY=VALUE, got {raw!r}")
    return key, val
