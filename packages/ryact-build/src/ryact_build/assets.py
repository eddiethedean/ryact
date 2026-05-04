from __future__ import annotations

import shutil
from pathlib import Path


def copy_file_into_dir(src: Path, dest_dir: Path) -> None:
    """Copy a single file into ``dest_dir`` preserving basename."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest_dir / src.name)


def merge_tree_into_dir(src_dir: Path, dest_dir: Path) -> None:
    """Copy each top-level child of ``src_dir`` into ``dest_dir`` (dirs merged)."""
    if not src_dir.is_dir():
        raise NotADirectoryError(str(src_dir))
    dest_dir.mkdir(parents=True, exist_ok=True)
    for child in src_dir.iterdir():
        target = dest_dir / child.name
        if child.is_dir():
            shutil.copytree(child, target, dirs_exist_ok=True)
        else:
            shutil.copy2(child, target)
