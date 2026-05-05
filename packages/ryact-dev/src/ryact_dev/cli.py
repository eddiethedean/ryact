from __future__ import annotations

import argparse
import os
import shlex
import subprocess
import sys
from collections.abc import Coroutine, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from rich.console import Console
from watchfiles import Change, DefaultFilter, awatch

console = Console()


class RepoRootNotFound(RuntimeError):
    pass


def _find_repo_root(start: Path) -> Path:
    cur = start.resolve()
    if cur.is_file():
        cur = cur.parent
    for p in [cur, *cur.parents]:
        if (p / "scripts" / "jsx_build.py").exists() and (p / "packages" / "ryact").exists():
            return p
    raise RepoRootNotFound(f"Could not find repo root from {start}. Expected scripts/jsx_build.py and packages/ryact/")


@dataclass(frozen=True)
class RunSpec:
    cmd: Sequence[str]
    cwd: Path


def _run_once(*, spec: RunSpec) -> int:
    proc = subprocess.run(spec.cmd, cwd=spec.cwd)
    return proc.returncode


class Runner:
    def __init__(self, *, cmd: Sequence[str], cwd: Path) -> None:
        self._cmd = cmd
        self._cwd = cwd
        self._proc: subprocess.Popen[bytes] | None = None

    def start(self) -> None:
        self.stop()
        self._proc = subprocess.Popen(self._cmd, cwd=self._cwd)

    def stop(self) -> None:
        if self._proc is None:
            return
        if self._proc.poll() is None:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                self._proc.kill()
                self._proc.wait()
        self._proc = None


def _print_phase(title: str) -> None:
    console.print(f"[bold]{title}[/bold]")


def _format_cmd(cmd: Sequence[str]) -> str:
    return " ".join(shlex.quote(x) for x in cmd)


def _parse_cmd(s: str) -> Sequence[str]:
    # shell-like quoting; avoids platform-specific "shell=True"
    return shlex.split(s)


def _tsx_filter() -> DefaultFilter:
    return DefaultFilter(
        ignore_dirs=(
            ".git",
            ".venv",
            "__pycache__",
            "node_modules",
            "build",
            "dist",
        ),
        ignore_entity_patterns=(),
    )


async def _watch_loop(
    *,
    watch_paths: Sequence[Path],
    build_cmd: Sequence[str],
    run_cmd: Sequence[str],
    repo_root: Path,
    persistent_run: bool,
) -> int:
    last_exit: int = 0
    runner = Runner(cmd=run_cmd, cwd=repo_root)

    async def rebuild_and_run(reason: str) -> None:
        nonlocal last_exit
        _print_phase(f"Build ({reason})")
        console.print(f"$ {_format_cmd(build_cmd)}")
        build_exit = _run_once(spec=RunSpec(cmd=build_cmd, cwd=repo_root))
        if build_exit != 0:
            last_exit = build_exit
            console.print(f"[red]Build failed[/red] (exit {build_exit}). Waiting for changes…")
            return

        _print_phase("Run")
        console.print(f"$ {_format_cmd(run_cmd)}")
        if persistent_run:
            runner.start()
            last_exit = 0
        else:
            last_exit = _run_once(spec=RunSpec(cmd=run_cmd, cwd=repo_root))

    await rebuild_and_run("initial")

    async for changes in awatch(*watch_paths, watch_filter=_tsx_filter()):
        # debounce a tiny bit to coalesce editor bursts
        import asyncio

        await asyncio.sleep(0.05)
        touched = sorted(
            {
                str(p)
                for kind, p in changes
                if kind != Change.deleted and Path(p).suffix in {".ts", ".tsx", ".js", ".jsx", ".json", ".css", ".md"}
            }
        )
        if not touched:
            continue
        await rebuild_and_run(", ".join(touched[:3]) + ("…" if len(touched) > 3 else ""))

        # In persistent mode, let the restarted process print a bit before the next rebuild.
        if persistent_run:
            await asyncio.sleep(0.02)

    runner.stop()
    return last_exit


def _cmd_jsx(args: argparse.Namespace) -> int:
    repo_root = _find_repo_root(Path.cwd())

    inp = Path(args.input).resolve()
    out = Path(args.out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)

    build_cmd = [
        sys.executable,
        str(repo_root / "scripts" / "jsx_build.py"),
        str(inp),
        "--out",
        str(out),
    ]

    run_cmd = _parse_cmd(args.run)

    watch_paths = [inp.parent]
    if args.watch is not None:
        watch_paths = [Path(p).resolve() for p in args.watch]

    console.print(f"[dim]repo_root[/dim] {repo_root}")
    console.print(f"[dim]watching[/dim] {', '.join(str(p) for p in watch_paths)}")

    if args.once:
        _print_phase("Build (once)")
        console.print(f"$ {_format_cmd(build_cmd)}")
        build_exit = _run_once(spec=RunSpec(cmd=build_cmd, cwd=repo_root))
        if build_exit != 0:
            return build_exit
        _print_phase("Run (once)")
        console.print(f"$ {_format_cmd(run_cmd)}")
        return _run_once(spec=RunSpec(cmd=run_cmd, cwd=repo_root))

    try:
        return _run_async(
            _watch_loop(
                watch_paths=watch_paths,
                build_cmd=build_cmd,
                run_cmd=run_cmd,
                repo_root=repo_root,
                persistent_run=bool(args.persistent_run),
            )
        )
    except KeyboardInterrupt:
        console.print("\n[dim]stopped[/dim]")
        return 130


def _cmd_test(args: argparse.Namespace) -> int:
    repo_root = _find_repo_root(Path.cwd())

    watch_paths = [repo_root]
    if args.watch is not None:
        watch_paths = [Path(p).resolve() for p in args.watch]

    pytest_cmd = ["pytest", *args.pytest_args]
    if args.default_env:
        pytest_cmd = ["env", "PYTEST_DISABLE_PLUGIN_AUTOLOAD=1", *pytest_cmd]

    console.print(f"[dim]repo_root[/dim] {repo_root}")
    console.print(f"[dim]watching[/dim] {', '.join(str(p) for p in watch_paths)}")

    async def loop() -> int:
        last_exit: int = 0

        async def run(reason: str) -> None:
            nonlocal last_exit
            _print_phase(f"Test ({reason})")
            console.print(f"$ {_format_cmd(pytest_cmd)}")
            last_exit = _run_once(spec=RunSpec(cmd=pytest_cmd, cwd=repo_root))

        await run("initial")

        async for changes in awatch(*watch_paths, watch_filter=_tsx_filter()):
            import asyncio

            await asyncio.sleep(0.05)
            touched = sorted(
                {
                    str(p)
                    for kind, p in changes
                    if kind != Change.deleted and Path(p).suffix in {".py", ".toml", ".yml", ".yaml"}
                }
            )
            if not touched:
                continue
            await run(", ".join(touched[:3]) + ("…" if len(touched) > 3 else ""))

        return last_exit

    try:
        return _run_async(loop())
    except KeyboardInterrupt:
        console.print("\n[dim]stopped[/dim]")
        return 130


def _run_async(coro: Coroutine[Any, Any, int]) -> int:
    # Keep this module dependency-free; avoid asyncio.run on 3.8 with nested loops.
    import asyncio

    return asyncio.run(coro)

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="ryact-dev", description="Vite-like dev loop for ryact.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    jsx = sub.add_parser(
        "jsx",
        help="Watch TSX/JSX, compile to Python, then run a Python command.",
    )
    jsx.add_argument("input", help="Entry TSX file (e.g. src/main.tsx)")
    jsx.add_argument("--out", required=True, help="Output Python file path (e.g. build/app.py)")
    jsx.add_argument(
        "--run",
        required=True,
        help=('Command to run after successful build (e.g. "python templates/ryact_jsx_app/ryact_runner.py")'),
    )
    jsx.add_argument(
        "--watch",
        action="append",
        help="Extra watch path(s). Can be passed multiple times. Defaults to input file directory.",
    )
    jsx.add_argument(
        "--persistent-run",
        action="store_true",
        help="Keep the runner process alive; restart it on rebuild (more Vite-like).",
    )
    jsx.add_argument("--once", action="store_true", help="Build+run once, no watching.")
    jsx.set_defaults(func=_cmd_jsx)

    test = sub.add_parser("test", help="Watch files and rerun pytest.")
    test.add_argument(
        "--watch",
        action="append",
        help="Watch path(s). Can be passed multiple times. Defaults to repo root.",
    )
    test.add_argument(
        "--default-env",
        action="store_true",
        help="Set PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 (recommended for this repo).",
    )
    test.add_argument("pytest_args", nargs=argparse.REMAINDER, help="Args passed through to pytest.")
    test.set_defaults(func=_cmd_test)

    args = parser.parse_args(argv)

    # Ensure deterministic output (useful in CI and logs)
    os.environ.setdefault("PYTHONUNBUFFERED", "1")

    rc = int(args.func(args))
    raise SystemExit(rc)
