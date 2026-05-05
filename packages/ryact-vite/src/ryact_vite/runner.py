from __future__ import annotations

import argparse
import os
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any

from .exceptions import RyactBuildImportError


def import_ryact_build_main():
    try:
        from ryact_build.cli import main as ryact_build_main  # type: ignore[import-untyped]
    except ImportError as e:
        raise RyactBuildImportError(
            "ryact-build is required (install the `ryact-build` package). "
            "From the monorepo: python -m pip install -e packages/ryact-build"
        ) from e
    return ryact_build_main


def run_ryact_build(argv: list[str]) -> int:
    """Run ``ryact-build`` in-process; forward exit code."""
    main = import_ryact_build_main()
    return int(main(argv))


def merge_default(key: str, cli_val: Any, config: dict[str, Any]) -> Any:
    if cli_val is not None:
        return cli_val
    return config.get(key)


def argv_bundle(
    *,
    cwd: Path,
    config: dict[str, Any],
    entry: Path | None,
    out_dir: Path | None,
    fmt: str | None,
    target: str | None,
    define: list[str] | None,
    inject: list[Path] | None,
    html: Path | None,
    assets: Path | None,
    minify: bool,
    clean: bool,
    verbose: bool,
    watch: bool,
) -> list[str]:
    sub = "watch" if watch else "bundle"
    e = merge_default("entry", entry, config)
    o = merge_default("outDir", out_dir, config)
    if e is None or o is None:
        raise ValueError(
            "missing --entry / --out-dir (or set entry + outDir in ryact-vite.json)"
        )
    cmd = [
        sub,
        "--cwd",
        str(cwd),
        "--entry",
        str(Path(e).expanduser()),
        "--out-dir",
        str(Path(o).expanduser()),
    ]
    fmt_f = merge_default("format", fmt, config)
    if fmt_f:
        cmd.extend(["--format", str(fmt_f)])
    tgt = merge_default("target", target, config)
    if tgt:
        cmd.extend(["--target", str(tgt)])
    defines = list(define or []) + list(config.get("define") or [])
    for d in defines:
        cmd.extend(["--define", str(d)])
    inject_paths: list[Path] = []
    if inject:
        inject_paths.extend(inject)
    for raw in config.get("inject") or []:
        inject_paths.append(Path(str(raw)))
    for inj in inject_paths:
        cmd.extend(["--inject", str(inj)])
    h = merge_default("html", html, config)
    if h:
        cmd.extend(["--html", str(Path(h).expanduser())])
    a = merge_default("assets", assets, config)
    if a:
        cmd.extend(["--assets", str(Path(a).expanduser())])
    if minify or config.get("minify"):
        cmd.append("--minify")
    if clean or config.get("clean"):
        cmd.append("--clean")
    if verbose or config.get("verbose"):
        cmd.append("--verbose")
    return cmd


def parse_preview_port(args: list[str], *, default: int = 4173) -> tuple[list[str], int]:
    """Strip ``--port`` / ``-p`` from *args* (Vite-style); return remaining args and port."""
    port = default
    out: list[str] = []
    i = 0
    while i < len(args):
        a = args[i]
        if a in ("--port", "-p") and i + 1 < len(args):
            port = int(args[i + 1])
            i += 2
            continue
        out.append(a)
        i += 1
    return out, port


def run_static_preview(*, out_dir: Path, port: int) -> int:
    """Serve *out_dir* with ``python -m http.server`` (stdlib)."""
    if not out_dir.is_dir():
        print(f"ryact-vite preview: not a directory: {out_dir}", file=sys.stderr)
        return 2
    print(f"serving {out_dir} at http://127.0.0.1:{port}/ (Ctrl+C to stop)")
    proc = subprocess.run(
        [sys.executable, "-m", "http.server", str(port)],
        cwd=out_dir,
        env=os.environ,
    )
    return int(proc.returncode)


def build_dev_namespace(cfg: dict[str, Any], args: argparse.Namespace) -> argparse.Namespace:
    """Build a namespace compatible with :func:`ryact_build.cli._build_bundle_config` (watch)."""
    ns = argparse.Namespace()
    e = merge_default("entry", getattr(args, "entry", None), cfg)
    o = merge_default("outDir", getattr(args, "out_dir", None), cfg)
    ns.entry = Path(str(e)) if e is not None else None
    ns.out_dir = Path(str(o)) if o is not None else None
    fmt = merge_default("format", getattr(args, "format", None), cfg)
    ns.format = fmt if fmt is not None else "esm"
    ns.target = merge_default("target", getattr(args, "target", None), cfg)
    ns.define = getattr(args, "define", None)
    ns.inject = getattr(args, "inject", None)
    ns.minify = bool(getattr(args, "minify", False)) or bool(cfg.get("minify"))
    ns.watch = True
    return ns


def run_dev(args: argparse.Namespace) -> int:
    """Watch + Rolldown rebuilds and serve ``out_dir`` over HTTP (optional livereload)."""
    try:
        from ryact_build.assets import copy_file_into_dir, merge_tree_into_dir  # type: ignore[import-untyped]
        from ryact_build.clean import UnsafeCleanError, clean_out_dir_contents  # type: ignore[import-untyped]
        from ryact_build.cli import (  # type: ignore[import-untyped]
            _build_bundle_config,
            _preflight_bundle,
            _resolve_path,
        )
        from ryact_build.exceptions import NativeExtensionUnavailableError  # type: ignore[import-untyped]
        from ryact_build.watch_run import run_watch_forever  # type: ignore[import-untyped]
    except ImportError as e:
        raise RyactBuildImportError(
            "ryact-build is required (install the `ryact-build` package). "
            "From the monorepo: python -m pip install -e packages/ryact-build"
        ) from e

    from .config import load_config
    from .dev_server import LiveReloadCounter, inject_livereload_into_html, start_dev_server

    cwd = (args.cwd if args.cwd is not None else Path.cwd()).resolve()
    cfg = load_config(cwd)
    ns = build_dev_namespace(cfg, args)

    if ns.entry is None or ns.out_dir is None:
        print(
            "ryact-vite dev: missing --entry / --out-dir (or entry + outDir in ryact-vite.json)",
            file=sys.stderr,
        )
        return 2

    injects = [_resolve_path(p, cwd) for p in (ns.inject or [])]
    entry = _resolve_path(ns.entry, cwd)

    hm = getattr(args, "html", None)
    hc = cfg.get("html")
    html_arg = hm if hm is not None else (Path(str(hc)) if hc else None)
    html_resolved = _resolve_path(html_arg, cwd) if html_arg is not None else None

    am = getattr(args, "assets", None)
    ac = cfg.get("assets")
    assets_arg = am if am is not None else (Path(str(ac)) if ac else None)
    assets_resolved = _resolve_path(assets_arg, cwd) if assets_arg is not None else None

    err = _preflight_bundle(entry=entry, html=html_resolved, assets=assets_resolved, injects=injects)
    if err is not None:
        return int(err)

    try:
        bundle_cfg = _build_bundle_config(ns, cwd, watch=True)
    except ValueError as e:
        print(f"ryact-vite: {e}", file=sys.stderr)
        return 2

    if bundle_cfg.target:
        print(
            "ryact-build: warning: --target is not yet wired to Rolldown in this release; ignoring.",
            file=sys.stderr,
        )

    clean = bool(getattr(args, "clean", False)) or bool(cfg.get("clean"))
    verbose = bool(getattr(args, "verbose", False)) or bool(cfg.get("verbose"))

    if clean:
        try:
            clean_out_dir_contents(out_dir=bundle_cfg.out_dir, cwd=cwd)
        except UnsafeCleanError as e:
            print(str(e), file=sys.stderr)
            return 2
    else:
        bundle_cfg.out_dir.mkdir(parents=True, exist_ok=True)

    port = getattr(args, "port", None)
    if port is None:
        port = int(cfg.get("devPort", 5173))
    host_s = getattr(args, "host", None)
    host = str(host_s if host_s is not None else (cfg.get("devHost") or "127.0.0.1"))

    no_lr = bool(getattr(args, "no_livereload", False))
    livereload_enabled = (not no_lr) and bool(cfg.get("livereload", True))

    live = LiveReloadCounter() if livereload_enabled else None

    if html_resolved is not None:
        copy_file_into_dir(html_resolved.resolve(), bundle_cfg.out_dir)
        print(f"copied {html_resolved} -> {bundle_cfg.out_dir / html_resolved.name}", file=sys.stderr)
        if livereload_enabled:
            inject_livereload_into_html(bundle_cfg.out_dir / html_resolved.name)
    if assets_resolved is not None:
        merge_tree_into_dir(assets_resolved.resolve(), bundle_cfg.out_dir)
        print(f"merged assets {assets_resolved} -> {bundle_cfg.out_dir}", file=sys.stderr)

    bound = threading.Event()

    def signal_bound() -> None:
        bound.set()

    server, _http_thread = start_dev_server(
        out_dir=bundle_cfg.out_dir.resolve(),
        host=host,
        port=port,
        livereload=live,
        on_bound=signal_bound,
    )
    bound.wait(timeout=5.0)

    print(f"ryact-vite dev: http://{host}:{port}/", file=sys.stderr)
    if livereload_enabled:
        print(
            "ryact-vite dev: livereload on successful rebuilds (injected into copied HTML when present)",
            file=sys.stderr,
        )
    else:
        print("ryact-vite dev: livereload disabled; refresh after rebuilds", file=sys.stderr)

    def on_complete(rc: int) -> None:
        if live is not None:
            live.on_rebuild(rc)

    try:
        rc_watch = run_watch_forever(
            cwd=cwd,
            config=bundle_cfg,
            verbose=verbose,
            on_rebuild_complete=on_complete,
        )
        return int(rc_watch)
    except NativeExtensionUnavailableError as e:
        print(str(e), file=sys.stderr)
        server.shutdown()
        return 127
