from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from ryact_build.cli import main


def test_static_merges_tree(tmp_path: Path) -> None:
    src = tmp_path / "static"
    src.mkdir()
    (src / "styles.css").write_text("body{}", encoding="utf8")
    nested = src / "img"
    nested.mkdir()
    (nested / "keep.txt").write_text("ok", encoding="utf8")
    out = tmp_path / "dist"

    rc = main(
        [
            "static",
            "--cwd",
            str(tmp_path),
            "--src",
            "static",
            "--to",
            "dist",
        ]
    )
    assert rc == 0
    assert (out / "styles.css").read_text(encoding="utf8") == "body{}"
    assert (out / "img" / "keep.txt").read_text(encoding="utf8") == "ok"


def test_static_invoked_as_python_m_module(tmp_path: Path) -> None:
    """``python -m ryact_build.cli`` must run ``main()`` (not exit without doing work)."""
    src = tmp_path / "static"
    src.mkdir()
    (src / "a.txt").write_text("z", encoding="utf8")
    out = tmp_path / "out"
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "ryact_build.cli",
            "static",
            "--cwd",
            str(tmp_path),
            "--src",
            "static",
            "--to",
            "out",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    assert (out / "a.txt").read_text(encoding="utf8") == "z"


def test_static_missing_src_returns_2(tmp_path: Path) -> None:
    rc = main(
        [
            "static",
            "--cwd",
            str(tmp_path),
            "--src",
            "does-not-exist",
            "--to",
            "out",
        ]
    )
    assert rc == 2
