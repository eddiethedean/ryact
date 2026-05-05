from __future__ import annotations

import importlib
import sys
from pathlib import Path
from typing import Any

from .bundle_config import BundleConfig
from .exceptions import NativeExtensionUnavailableError


def _load_native_module() -> Any:
    """Import `ryact_build._native`; overridden in tests."""
    try:
        return importlib.import_module("ryact_build._native")
    except ImportError as e:
        raise NativeExtensionUnavailableError(
            "Could not import ryact_build._native (build the package with maturin: "
            "'maturin develop' from packages/ryact-build)."
        ) from e


def run_bundle_roll_from_config(*, config: BundleConfig, cwd: Path, verbose: bool) -> int:
    """Run one Rolldown bundle using the native extension (`ryact_build._native`)."""
    if config.injects:
        print(
            "ryact-build: warning: --inject is not yet implemented for the Rolldown backend; ignoring.",
            file=sys.stderr,
        )
    _native = _load_native_module()

    defines: dict[str, str] | None = None
    if config.defines:
        defines = dict(sorted(config.defines, key=lambda kv: kv[0]))

    if verbose:
        print(
            "ryact-build (rolldown): entry="
            f"{config.entry.resolve()} out_dir={config.out_dir.resolve()} "
            f"cwd={cwd.resolve()} format={config.format} minify={config.minify}",
            file=sys.stderr,
        )

    try:
        _native.bundle_roll(
            str(config.entry.resolve()),
            str(config.out_dir.resolve()),
            str(cwd.resolve()),
            config.format,
            config.minify,
            verbose,
            defines,
        )
    except Exception as e:
        print(f"ryact-build: bundle failed: {e}", file=sys.stderr)
        return 1
    return 0
