from __future__ import annotations

import argparse
import shutil
from pathlib import Path


def _copytree(src: Path, dst: Path) -> None:
    if dst.exists():
        raise SystemExit(f"Destination already exists: {dst}")
    shutil.copytree(src, dst)


def main() -> None:
    parser = argparse.ArgumentParser(description="Scaffold a minimal JSX/TSX ryact app.")
    parser.add_argument("path", type=Path, help="Where to create the app directory")
    parser.add_argument(
        "--template",
        default="ryact_jsx_app",
        help="Template name under templates/ (default: ryact_jsx_app)",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    template_dir = repo_root / "templates" / args.template
    if not template_dir.exists():
        raise SystemExit(f"Template not found: {template_dir}")

    _copytree(template_dir, args.path)
    print(f"Created {args.path}")


if __name__ == "__main__":
    main()
