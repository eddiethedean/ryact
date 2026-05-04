from __future__ import annotations

import argparse
import shutil
import sys
from collections.abc import Sequence
from pathlib import Path

from .assets import copy_file_into_dir, merge_tree_into_dir
from .bundle_config import BundleConfig, bundle_argv, parse_define_arg
from .clean import UnsafeCleanError, clean_out_dir_contents
from .esbuild import run_esbuild
from .exceptions import EsbuildNotFoundError
from .html_check import warn_missing_script_refs
from .pyx_step import compile_pyx_file


def _resolve_path(path: Path, cwd: Path) -> Path:
    return path.resolve() if path.is_absolute() else (cwd / path).resolve()


def _strip_leading_dd(args: list[str] | None) -> list[str]:
    out = list(args or [])
    while out and out[0] == "--":
        out = out[1:]
    return out


def _preflight_bundle(
    *,
    entry: Path,
    html: Path | None,
    assets: Path | None,
    injects: list[Path],
) -> int | None:
    if not entry.is_file():
        print(f"ryact-build: entry not found: {entry}", file=sys.stderr)
        return 2
    if html is not None and not html.is_file():
        print(f"ryact-build: --html not found: {html}", file=sys.stderr)
        return 2
    if assets is not None and not assets.is_dir():
        print(f"ryact-build: --assets is not a directory: {assets}", file=sys.stderr)
        return 2
    for inj in injects:
        if not inj.is_file():
            print(f"ryact-build: --inject not found: {inj}", file=sys.stderr)
            return 2
    return None


def _preflight_pyx(input_path: Path) -> int | None:
    if not input_path.is_file():
        print(f"ryact-build: --input not found: {input_path}", file=sys.stderr)
        return 2
    if not str(input_path).endswith(".pyx"):
        print("ryact-build: warning: --input does not end with .pyx", file=sys.stderr)
    return None


def _build_bundle_config(args: argparse.Namespace, cwd: Path, *, watch: bool) -> BundleConfig:
    entry = _resolve_path(args.entry, cwd)
    out_dir = _resolve_path(args.out_dir, cwd)
    defines: list[tuple[str, str]] = []
    for d in args.define or []:
        defines.append(parse_define_arg(d))
    injects: list[Path] = []
    for inj in args.inject or []:
        injects.append(_resolve_path(inj, cwd))
    extra = _strip_leading_dd(list(args.esbuild_extra or []))
    return BundleConfig(
        entry=entry,
        out_dir=out_dir,
        minify=bool(args.minify),
        format=args.format,
        target=args.target,
        defines=tuple(defines),
        injects=tuple(injects),
        extra=tuple(extra),
        watch=watch,
    )


def _run_esbuild_pipeline(
    *,
    cwd: Path,
    config: BundleConfig,
    html: Path | None,
    assets: Path | None,
    verbose: bool,
    clean: bool,
    copy_static_after: bool,
    run_html_check: bool,
) -> int:
    if shutil.which("node") is None:
        print("Node.js is required for esbuild (node not found on PATH).", file=sys.stderr)
        return 127

    if clean:
        try:
            clean_out_dir_contents(out_dir=config.out_dir, cwd=cwd)
        except UnsafeCleanError as e:
            print(str(e), file=sys.stderr)
            return 2
    else:
        config.out_dir.mkdir(parents=True, exist_ok=True)

    if config.watch:
        if html is not None:
            copy_file_into_dir(html.resolve(), config.out_dir)
            print(f"copied {html} -> {config.out_dir / html.name}")
        if assets is not None:
            merge_tree_into_dir(assets.resolve(), config.out_dir)
            print(f"merged assets {assets} -> {config.out_dir}")

    argv = bundle_argv(config)
    try:
        rc = run_esbuild(argv, cwd=cwd, verbose=verbose)
    except EsbuildNotFoundError as e:
        print(str(e), file=sys.stderr)
        return 127
    if rc != 0:
        return rc

    if copy_static_after:
        if html is not None:
            copy_file_into_dir(html.resolve(), config.out_dir)
            print(f"copied {html} -> {config.out_dir / html.name}")
        if assets is not None:
            merge_tree_into_dir(assets.resolve(), config.out_dir)
            print(f"merged assets {assets} -> {config.out_dir}")
        if html is not None and run_html_check:
            warn_missing_script_refs(html_path=config.out_dir / html.name, out_dir=config.out_dir)
    return 0


def _cmd_pyx(args: argparse.Namespace) -> int:
    inp = args.input.resolve()
    err = _preflight_pyx(inp)
    if err is not None:
        return err
    compile_pyx_file(
        input_path=inp,
        output_path=args.out.resolve(),
        mode=args.mode,
    )
    print(f"wrote {args.out}")
    return 0


def _cmd_bundle(args: argparse.Namespace) -> int:
    cwd = (args.cwd if args.cwd is not None else Path.cwd()).resolve()
    injects = [_resolve_path(p, cwd) for p in (args.inject or [])]
    entry = _resolve_path(args.entry, cwd)
    html = args.html.resolve() if args.html is not None else None
    err = _preflight_bundle(entry=entry, html=html, assets=args.assets, injects=injects)
    if err is not None:
        return err
    try:
        cfg = _build_bundle_config(args, cwd, watch=False)
    except ValueError as e:
        print(f"ryact-build: {e}", file=sys.stderr)
        return 2
    return _run_esbuild_pipeline(
        cwd=cwd,
        config=cfg,
        html=args.html,
        assets=args.assets,
        verbose=bool(args.verbose),
        clean=bool(args.clean),
        copy_static_after=True,
        run_html_check=True,
    )


def _cmd_watch(args: argparse.Namespace) -> int:
    cwd = (args.cwd if args.cwd is not None else Path.cwd()).resolve()
    injects = [_resolve_path(p, cwd) for p in (args.inject or [])]
    entry = _resolve_path(args.entry, cwd)
    html = args.html.resolve() if args.html is not None else None
    err = _preflight_bundle(entry=entry, html=html, assets=args.assets, injects=injects)
    if err is not None:
        return err
    try:
        cfg = _build_bundle_config(args, cwd, watch=True)
    except ValueError as e:
        print(f"ryact-build: {e}", file=sys.stderr)
        return 2
    return _run_esbuild_pipeline(
        cwd=cwd,
        config=cfg,
        html=args.html,
        assets=args.assets,
        verbose=bool(args.verbose),
        clean=bool(args.clean),
        copy_static_after=False,
        run_html_check=False,
    )


def _cmd_all(args: argparse.Namespace) -> int:
    if args.pyx is not None:
        if args.pyx_out is None:
            print("--pyx-out is required when --pyx is set", file=sys.stderr)
            return 2
        px = args.pyx.resolve()
        err = _preflight_pyx(px)
        if err is not None:
            return err
        compile_pyx_file(
            input_path=px,
            output_path=args.pyx_out.resolve(),
            mode=args.pyx_mode,
        )
        print(f"wrote {args.pyx_out}")

    cwd = (args.cwd if args.cwd is not None else Path.cwd()).resolve()
    injects = [_resolve_path(p, cwd) for p in (args.inject or [])]
    entry = _resolve_path(args.entry, cwd)
    html = args.html.resolve() if args.html is not None else None
    err = _preflight_bundle(entry=entry, html=html, assets=args.assets, injects=injects)
    if err is not None:
        return err
    try:
        cfg = _build_bundle_config(args, cwd, watch=False)
    except ValueError as e:
        print(f"ryact-build: {e}", file=sys.stderr)
        return 2
    return _run_esbuild_pipeline(
        cwd=cwd,
        config=cfg,
        html=args.html,
        assets=args.assets,
        verbose=bool(args.verbose),
        clean=bool(args.clean),
        copy_static_after=True,
        run_html_check=True,
    )


def _add_core_bundle_flags(p: argparse.ArgumentParser) -> None:
    p.add_argument("--entry", type=Path, required=True)
    p.add_argument("--out-dir", type=Path, required=True)
    p.add_argument("--format", choices=("esm", "iife", "cjs"), default="esm")
    p.add_argument("--target", type=str, default=None, metavar="ESVERSION")
    p.add_argument(
        "--define",
        action="append",
        default=None,
        metavar="KEY=VALUE",
        help="Forwarded as --define:KEY=VALUE (repeatable).",
    )
    p.add_argument(
        "--inject",
        action="append",
        default=None,
        type=Path,
        metavar="FILE",
        help="Forwarded as --inject:FILE (repeatable); paths relative to --cwd unless absolute.",
    )
    p.add_argument(
        "--html",
        type=Path,
        default=None,
        help="Static HTML: copied after bundle (bundle/all) or before watch (watch).",
    )
    p.add_argument(
        "--assets",
        type=Path,
        default=None,
        help="Merge top-level files/dirs from this folder into out-dir (after bundle).",
    )
    p.add_argument("--minify", action="store_true")
    p.add_argument(
        "--clean",
        action="store_true",
        help="Delete contents of --out-dir before build; only if out-dir is a subdirectory of --cwd.",
    )
    p.add_argument("--verbose", action="store_true", help="Print the esbuild argv before running.")
    p.add_argument(
        "esbuild_extra",
        nargs=argparse.REMAINDER,
        help="Extra args after -- are forwarded to esbuild.",
    )


def _add_bundle_arguments(p: argparse.ArgumentParser) -> None:
    p.add_argument("--cwd", type=Path, default=None, help="Working directory for esbuild (default: pwd).")
    _add_core_bundle_flags(p)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="ryact-build",
        description="Narrow static web build: esbuild (JS/TS/JSX/TSX) + optional PYX→Python.",
    )
    sub = p.add_subparsers(dest="command", required=True)

    pyx = sub.add_parser("pyx", help="Compile .pyx to Python using ryact_pyx.")
    pyx.add_argument("--input", type=Path, required=True)
    pyx.add_argument("--out", type=Path, required=True)
    pyx.add_argument("--mode", choices=("module", "expr"), default="module")
    pyx.set_defaults(func=_cmd_pyx)

    bundle = sub.add_parser("bundle", help="Run esbuild --bundle on a JS/TS/JSX/TSX entry.")
    _add_bundle_arguments(bundle)
    bundle.set_defaults(func=_cmd_bundle)

    watch = sub.add_parser(
        "watch",
        help="Run esbuild --bundle --watch; copies --html/--assets into out-dir once before watch.",
    )
    _add_bundle_arguments(watch)
    watch.set_defaults(func=_cmd_watch)

    all_p = sub.add_parser("all", help="Optional PYX compile, then bundle + optional static copies.")
    all_p.add_argument("--cwd", type=Path, default=None, help="Working directory for esbuild (default: pwd).")
    all_p.add_argument("--pyx", type=Path, default=None)
    all_p.add_argument("--pyx-out", type=Path, default=None)
    all_p.add_argument("--pyx-mode", choices=("module", "expr"), default="module")
    _add_core_bundle_flags(all_p)
    all_p.set_defaults(func=_cmd_all)

    return p


def main(argv: Sequence[str] | None = None) -> int:
    raw = list(sys.argv[1:] if argv is None else argv)
    args = build_parser().parse_args(raw)
    return int(args.func(args))


def entrypoint() -> None:
    raise SystemExit(main())
