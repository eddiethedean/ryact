"""Smoke tests: both documented minimal Ryact build paths must succeed.

1. **Browser bundle** — `ryact-build bundle` (Rolldown) on `packages/ryact-build/tests/fixtures/mini_web`.
2. **TSX → Python** — `python scripts/jsx_build.py` (uses `ryact-jsx`) on `templates/ryact_jsx_app/src/main.tsx`.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.jsx_to_py import try_resolve_ryact_jsx_binary

_REPO_ROOT = Path(__file__).resolve().parents[1]


def test_minimal_ryact_build_bundle() -> None:
    """`ryact-build bundle` produces JS + copied HTML (mini_web fixture)."""
    try:
        from ryact_build.cli import main
    except ImportError as e:
        pytest.skip(f"ryact-build not installed: {e}")

    mini = _REPO_ROOT / "packages" / "ryact-build" / "tests" / "fixtures" / "mini_web"
    # `--out-dir` must be a subdirectory of `--cwd` (resolved) when using `--clean`.
    dist = mini / "dist"
    if dist.is_dir():
        shutil.rmtree(dist)

    entry = mini / "src" / "entry.ts"
    html = mini / "index.html"

    rc = main(
        [
            "bundle",
            "--cwd",
            str(_REPO_ROOT),
            "--entry",
            str(entry),
            "--out-dir",
            str(dist),
            "--html",
            str(html),
            "--clean",
        ]
    )
    assert rc == 0, "ryact-build bundle failed"
    assert (dist / "entry.js").is_file()
    assert (dist / "index.html").is_file()
    assert "answer" in (dist / "entry.js").read_text(encoding="utf8")


def test_minimal_jsx_template_compiles_to_python(tmp_path: Path) -> None:
    """`scripts/jsx_build.py` compiles the template TSX to Python via `ryact-jsx`."""
    if try_resolve_ryact_jsx_binary(_REPO_ROOT) is None:
        pytest.skip(
            "ryact-jsx not available (build packages/ryact-jsx or set RYACT_JSX_TO_PY)"
        )

    out_py = tmp_path / "app.py"
    src_tsx = _REPO_ROOT / "templates" / "ryact_jsx_app" / "src" / "main.tsx"
    script = _REPO_ROOT / "scripts" / "jsx_build.py"

    proc = subprocess.run(
        [
            sys.executable,
            str(script),
            str(src_tsx),
            "--out",
            str(out_py),
        ],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    generated = out_py.read_text(encoding="utf8")
    assert "from ryact import" in generated
    assert "__ryact_jsx_source__" in generated
