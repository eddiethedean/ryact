from __future__ import annotations

import os
import shutil
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import cast


@dataclass(frozen=True)
class TransformResult:
    code: str


def _ryact_jsx_target_names() -> list[str]:
    if sys.platform == "win32":
        return ["ryact-jsx.exe"]
    return ["ryact-jsx"]


def resolve_ryact_jsx_binary(repo_root: Path) -> Path:
    """
    Resolve the `ryact-jsx` executable (TSX/JSX → Python).

    Order: `RYACT_JSX_TO_PY`, `PATH`, then built artifacts under
    `packages/ryact-jsx/target/{release,debug}/`.
    """
    env = os.environ.get("RYACT_JSX_TO_PY")
    if env:
        p = Path(env).expanduser()
        if p.is_file():
            return p.resolve()
        raise FileNotFoundError(f"RYACT_JSX_TO_PY is set but not a file: {p}")

    for name in _ryact_jsx_target_names():
        which = shutil.which(name)
        if which:
            return Path(which).resolve()

    for profile in ("release", "debug"):
        for name in _ryact_jsx_target_names():
            candidate = (repo_root / "packages" / "ryact-jsx" / "target" / profile / name).resolve()
            if candidate.is_file():
                return candidate

    raise FileNotFoundError(
        "Could not find ryact-jsx. Build it with:\n"
        "  cargo build --release --manifest-path packages/ryact-jsx/Cargo.toml\n"
        "Or set RYACT_JSX_TO_PY to the binary path, or install ryact-jsx on PATH."
    )


def try_resolve_ryact_jsx_binary(repo_root: Path) -> Path | None:
    try:
        return resolve_ryact_jsx_binary(repo_root)
    except FileNotFoundError:
        return None


def jsx_to_python(*, path: Path, mode: str = "expr") -> TransformResult:
    repo_root = Path(__file__).resolve().parents[1]
    binary = resolve_ryact_jsx_binary(repo_root)

    proc = subprocess.run(
        [str(binary), str(path), "--mode", mode],
        check=True,
        capture_output=True,
        text=True,
        cwd=repo_root,
    )
    return TransformResult(code=proc.stdout)


def eval_compiled(code: str, scope: dict[str, object] | None = None) -> object:
    if scope is None:
        scope = {}

    g: dict[str, object] = {}
    loc: dict[str, object] = {}

    ryact = __import__("ryact")
    g["h"] = ryact.h
    g["Fragment"] = ryact.Fragment

    if "def render" in code:
        exec(code, g, loc)
        fn = loc.get("render")
        assert callable(fn)
        render = cast(Callable[[dict[str, object]], object], fn)
        return render(scope)

    loc["scope"] = scope
    # Evaluate free identifiers from the provided scope (e.g. `{n}` -> `(n)`).
    loc.update(scope)
    return eval(code, g, loc)
