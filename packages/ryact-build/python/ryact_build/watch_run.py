from __future__ import annotations

import sys
import threading
import time
from collections.abc import Callable
from pathlib import Path

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from .bundle_config import BundleConfig
from .native_roll import run_bundle_roll_from_config


def _debounced(fn: Callable[[], None], delay_s: float) -> Callable[[], None]:
    lock = threading.Lock()
    timer: list[threading.Timer | None] = [None]

    def schedule() -> None:
        with lock:
            if timer[0] is not None:
                timer[0].cancel()
            t = threading.Timer(delay_s, _run)
            timer[0] = t
            t.daemon = True
            t.start()

    def _run() -> None:
        with lock:
            timer[0] = None
        fn()

    return schedule


def run_watch_forever(
    *,
    cwd: Path,
    config: BundleConfig,
    verbose: bool,
) -> int:
    """Rebuild with Rolldown when source files under cwd change."""

    def rebuild() -> None:
        try:
            rc = run_bundle_roll_from_config(config=config, cwd=cwd, verbose=verbose)
        except Exception as e:
            print(f"ryact-build: rebuild failed: {e}", file=sys.stderr)
            return
        if rc != 0:
            print(f"ryact-build: rebuild exited with code {rc}", file=sys.stderr)

    schedule = _debounced(lambda: rebuild(), 0.35)
    try:
        rc0 = run_bundle_roll_from_config(config=config, cwd=cwd, verbose=verbose)
    except Exception as e:
        print(str(e), file=sys.stderr)
        return 127
    if rc0 != 0:
        return rc0

    class _H(FileSystemEventHandler):
        _suffixes = {".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".json", ".css"}

        def on_any_event(self, event):  # type: ignore[no-untyped-def]
            if event.is_directory:
                return
            p = getattr(event, "src_path", "") or ""
            if any(str(p).endswith(s) for s in self._suffixes):
                schedule()

    observer = Observer()
    observer.schedule(_H(), str(cwd), recursive=True)
    observer.start()
    print("ryact-build: watching for changes (Ctrl+C to stop)...", file=sys.stderr)
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        print("", file=sys.stderr)
    finally:
        observer.stop()
        observer.join(timeout=5)
    return 0
