from __future__ import annotations

from pathlib import Path

import pytest
from ryact_build.clean import UnsafeCleanError, clean_out_dir_contents


def test_clean_removes_children(tmp_path: Path) -> None:
    cwd = tmp_path / "proj"
    out = cwd / "dist"
    out.mkdir(parents=True)
    (out / "a.js").write_text("x", encoding="utf8")
    sub = out / "sub"
    sub.mkdir()
    (sub / "b.txt").write_text("y", encoding="utf8")
    clean_out_dir_contents(out_dir=out, cwd=cwd)
    assert list(out.iterdir()) == []


def test_clean_refuses_out_equals_cwd(tmp_path: Path) -> None:
    cwd = tmp_path / "proj"
    cwd.mkdir()
    with pytest.raises(UnsafeCleanError):
        clean_out_dir_contents(out_dir=cwd, cwd=cwd)


def test_clean_refuses_outside_cwd(tmp_path: Path) -> None:
    cwd = tmp_path / "proj"
    cwd.mkdir()
    other = tmp_path / "other"
    other.mkdir()
    with pytest.raises(UnsafeCleanError):
        clean_out_dir_contents(out_dir=other, cwd=cwd)
