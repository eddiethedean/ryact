from __future__ import annotations

import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import cast


@dataclass(frozen=True)
class TransformResult:
    code: str


def jsx_to_python(*, path: Path, mode: str = "expr") -> TransformResult:
    repo_root = Path(__file__).resolve().parents[1]
    transform = repo_root / "scripts" / "jsx_to_py_transform.mjs"

    proc = subprocess.run(
        ["node", str(transform), str(path), "--mode", mode],
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
