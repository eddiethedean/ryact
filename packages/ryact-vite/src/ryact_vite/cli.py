from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from .config import CONFIG_FILENAME, default_config_template, load_config
from .exceptions import RyactBuildImportError
from .runner import argv_bundle, parse_preview_port, run_dev, run_ryact_build, run_static_preview


def _template_config_text() -> str:
    return json.dumps(default_config_template(), indent=2) + "\n"


def _cmd_init_config(cwd: Path) -> int:
    dest = cwd / CONFIG_FILENAME
    if dest.exists():
        print(f"refusing to overwrite existing file: {dest}", file=sys.stderr)
        return 1
    dest.write_text(_template_config_text(), encoding="utf8")
    print(f"wrote {dest}")
    return 0


def _add_bundle_like_flags(p: argparse.ArgumentParser) -> None:
    p.add_argument("--entry", type=Path, default=None, help="Bundle entry (default: ryact-vite.json).")
    p.add_argument("--out-dir", type=Path, default=None, help="Output directory (default: ryact-vite.json).")
    p.add_argument("--format", type=str, default=None, choices=("esm", "iife", "cjs"))
    p.add_argument("--target", type=str, default=None, metavar="ESVERSION")
    p.add_argument("--define", action="append", default=None, metavar="KEY=VALUE")
    p.add_argument("--inject", action="append", default=None, type=Path, metavar="FILE")
    p.add_argument("--html", type=Path, default=None)
    p.add_argument("--assets", type=Path, default=None)
    p.add_argument("--minify", action="store_true")
    p.add_argument("--clean", action="store_true")
    p.add_argument("--verbose", action="store_true")


def _cmd_dev(args: argparse.Namespace) -> int:
    """Watch Rolldown output and serve *out-dir* locally (optional livereload)."""
    try:
        return run_dev(args)
    except RyactBuildImportError as e:
        print(str(e), file=sys.stderr)
        return 127


def _cmd_build_like(args: argparse.Namespace, *, watch: bool) -> int:
    cwd = (args.cwd if args.cwd is not None else Path.cwd()).resolve()
    cfg = load_config(cwd)
    try:
        argv = argv_bundle(
            cwd=cwd,
            config=cfg,
            entry=args.entry,
            out_dir=args.out_dir,
            fmt=args.format,
            target=args.target,
            define=args.define,
            inject=args.inject,
            html=args.html,
            assets=args.assets,
            minify=bool(args.minify),
            clean=bool(args.clean),
            verbose=bool(args.verbose),
            watch=watch,
        )
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 2
    try:
        return run_ryact_build(argv)
    except RyactBuildImportError as e:
        print(str(e), file=sys.stderr)
        return 127


def _strip_leading_dd(args: list[str]) -> list[str]:
    out = list(args)
    while out and out[0] == "--":
        out = out[1:]
    return out


def _cmd_preview(args: argparse.Namespace) -> int:
    cwd = (args.cwd if args.cwd is not None else Path.cwd()).resolve()
    cfg = load_config(cwd)
    rest, port = parse_preview_port(
        _strip_leading_dd(list(args.rest)),
        default=int(cfg.get("previewPort", 4173)),
    )
    if rest:
        print(f"ryact-vite preview: ignoring unsupported args: {' '.join(rest)}", file=sys.stderr)
    out = args.out_dir
    if out is None:
        out = cfg.get("outDir")
    if out is None:
        out = Path("dist")
    out_dir = (cwd / Path(out)).resolve() if not Path(out).is_absolute() else Path(out).resolve()
    return run_static_preview(out_dir=out_dir, port=port)


def _cmd_exec(args: argparse.Namespace) -> int:
    cwd = (args.cwd if args.cwd is not None else Path.cwd()).resolve()
    raw = _strip_leading_dd(list(args.ryact_build_args))
    if not raw:
        print("exec requires a ryact-build subcommand, e.g. ryact-vite exec bundle --help", file=sys.stderr)
        return 2
    argv = [*raw]
    # Insert --cwd after subcommand if user did not pass --cwd
    if "--cwd" not in argv and "-C" not in argv:
        sub = argv[0]
        rest = argv[1:]
        argv = [sub, "--cwd", str(cwd), *rest]
    try:
        return run_ryact_build(argv)
    except RyactBuildImportError as e:
        print(str(e), file=sys.stderr)
        return 127


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="ryact-vite",
        description="Browser build helpers via ryact-build (Rolldown / Rust) — no Node.js.",
    )
    p.add_argument(
        "--cwd",
        type=Path,
        default=None,
        help="Project root for resolving paths (default: current directory).",
    )
    sub = p.add_subparsers(dest="command", required=True)

    b = sub.add_parser("build", help="Production bundle (ryact-build bundle).")
    _add_bundle_like_flags(b)
    b.set_defaults(func=lambda a: _cmd_build_like(a, watch=False))

    d = sub.add_parser(
        "dev",
        help="Serve out-dir over HTTP + ryact-build watch (Rolldown); optional livereload.",
    )
    _add_bundle_like_flags(d)
    d.add_argument(
        "--port",
        type=int,
        default=None,
        metavar="P",
        help="Dev server port (default: ryact-vite.json devPort or 5173).",
    )
    d.add_argument(
        "--host",
        type=str,
        default=None,
        metavar="ADDR",
        help="Bind address (default: ryact-vite.json devHost or 127.0.0.1).",
    )
    d.add_argument(
        "--no-livereload",
        action="store_true",
        help="Disable polling livereload (refresh manually after rebuilds).",
    )
    d.set_defaults(func=_cmd_dev)

    pv = sub.add_parser(
        "preview",
        help="Serve the output folder with Python's http.server (like vite preview, without Node).",
    )
    pv.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="Directory to serve (default: outDir from ryact-vite.json or ./dist).",
    )
    pv.add_argument(
        "rest",
        nargs=argparse.REMAINDER,
        help="Optional --port / -p (e.g. -- --port 8080).",
    )
    pv.set_defaults(func=_cmd_preview)

    ex = sub.add_parser(
        "exec",
        help="Pass through to ryact-build (e.g. ryact-vite exec bundle --entry ... --out-dir ...).",
    )
    ex.add_argument(
        "ryact_build_args",
        nargs=argparse.REMAINDER,
        help="Subcommand and flags for ryact-build; --cwd defaults to this tool's --cwd.",
    )
    ex.set_defaults(func=_cmd_exec)

    ic = sub.add_parser("init-config", help=f"Write starter {CONFIG_FILENAME} into --cwd.")

    def _init_dispatch(a: argparse.Namespace) -> int:
        root = (a.cwd if a.cwd is not None else Path.cwd()).resolve()
        return _cmd_init_config(root)

    ic.set_defaults(func=_init_dispatch)

    return p


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(list(argv if argv is not None else sys.argv[1:]))
    return int(args.func(args))


def entrypoint() -> None:
    raise SystemExit(main())


def _template_vite_config_text() -> str:
    """Compatibility alias for ``_template_config_text`` (historical name)."""
    return _template_config_text()
