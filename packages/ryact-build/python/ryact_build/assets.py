from __future__ import annotations

import shutil
from pathlib import Path


def _reject_symlink_outside_src(path: Path, src_dir: Path) -> None:
    if not path.is_symlink():
        return
    src_root = src_dir.resolve()
    if not path.resolve().is_relative_to(src_root):
        raise ValueError(f"symlink escapes source directory: {path}")


def copy_file_into_dir(src: Path, dest_dir: Path) -> None:
    """Copy a single file into ``dest_dir`` preserving basename."""
    _reject_symlink_outside_src(src, src.parent)
    dest_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest_dir / src.name)


def merge_tree_into_dir(src_dir: Path, dest_dir: Path) -> None:
    """Copy each top-level child of ``src_dir`` into ``dest_dir`` (dirs merged)."""
    if not src_dir.is_dir():
        raise NotADirectoryError(str(src_dir))
    dest_dir.mkdir(parents=True, exist_ok=True)
    for child in src_dir.iterdir():
        _reject_symlink_outside_src(child, src_dir)
        target = dest_dir / child.name
        if child.is_dir() and not child.is_symlink():
            shutil.copytree(child, target, dirs_exist_ok=True, symlinks=False)
        else:
            shutil.copy2(child, target, follow_symlinks=False)
