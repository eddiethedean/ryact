from __future__ import annotations

import argparse
import shutil
import sys
from collections.abc import Sequence
from pathlib import Path

from .exceptions import ViteNotFoundError
from .runner import run_vite


def _template_vite_config_text() -> str:
    p = Path(__file__).resolve().parent / "templates" / "vite.config.ryact.mjs"
    return p.read_text(encoding="utf8")


def _strip_leading_dd(args: list[str]) -> list[str]:
    out = list(args)
    while out and out[0] == "--":
        out = out[1:]
    return out


def _cmd_init_config(cwd: Path) -> int:
    dest = cwd / "vite.config.ryact.mjs"
    if dest.exists():
        print(f"refusing to overwrite existing file: {dest}", file=sys.stderr)
        return 1
    dest.write_text(_template_vite_config_text(), encoding="utf8")
    print(f"wrote {dest}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="ryact-vite",
        description="Run the Node Vite CLI from a Ryact-friendly Python entrypoint (browser dist/ workflow).",
    )
    p.add_argument(
        "--cwd",
        type=Path,
        default=None,
        help="Vite project root (default: current working directory).",
    )
    sub = p.add_subparsers(dest="command", required=True)

    for name, help_ in (
        ("dev", "Start Vite dev server (vite dev)."),
        ("build", "Production build (vite build)."),
        ("preview", "Preview production build (vite preview)."),
    ):
        sp = sub.add_parser(name, help=help_)
        sp.add_argument(
            "vite_args",
            nargs=argparse.REMAINDER,
            help="Extra arguments forwarded to Vite (use -- before flags if your shell requires it).",
        )

    ex = sub.add_parser("exec", help="Run vite with an arbitrary first argument (e.g. ryact-vite exec optimize).")
    ex.add_argument("vite_args", nargs=argparse.REMAINDER, help="Subcommand and args, e.g. optimize --force")

    sub.add_parser("init-config", help="Write vite.config.ryact.mjs into --cwd (no overwrite).")

    return p


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(list(argv if argv is not None else sys.argv[1:]))
    cwd = (args.cwd if args.cwd is not None else Path.cwd()).resolve()

    if args.command == "init-config":
        return _cmd_init_config(cwd)

    raw: list[str] = list(args.vite_args)
    raw = _strip_leading_dd(raw)

    if args.command == "exec":
        if not raw:
            print("exec requires at least one argument (vite subcommand)", file=sys.stderr)
            return 2
        vite_args = raw
    else:
        vite_args = [args.command, *raw]

    if shutil.which("node") is None:
        print("Node.js is required to run Vite (node not found on PATH).", file=sys.stderr)
        return 127

    try:
        return run_vite(vite_args, cwd=cwd)
    except ViteNotFoundError as e:
        print(str(e), file=sys.stderr)
        return 127


def entrypoint() -> None:
    raise SystemExit(main())
