from __future__ import annotations

from pathlib import Path

from ryact_build.assets import copy_file_into_dir, merge_tree_into_dir


def test_copy_file_into_dir(tmp_path: Path) -> None:
    src = tmp_path / "index.html"
    src.write_text("<html></html>", encoding="utf8")
    dest = tmp_path / "dist"
    copy_file_into_dir(src, dest)
    assert (dest / "index.html").read_text(encoding="utf8") == "<html></html>"


def test_merge_tree_into_dir(tmp_path: Path) -> None:
    public = tmp_path / "public"
    public.mkdir()
    (public / "f.txt").write_text("x", encoding="utf8")
    sub = public / "sub"
    sub.mkdir()
    (sub / "n.txt").write_text("y", encoding="utf8")
    dest = tmp_path / "dist"
    merge_tree_into_dir(public, dest)
    assert (dest / "f.txt").read_text(encoding="utf8") == "x"
    assert (dest / "sub" / "n.txt").read_text(encoding="utf8") == "y"
