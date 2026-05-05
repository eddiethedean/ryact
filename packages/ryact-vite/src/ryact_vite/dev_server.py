from __future__ import annotations

import json
import threading
from collections.abc import Callable
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse

LIVERELOAD_JS = """(() => {
  let last = null;
  const tick = async () => {
    try {
      const r = await fetch("/__ryact_livereload?v=" + Date.now());
      const j = await r.json();
      if (last === null) last = j.v;
      else if (j.v !== last) { location.reload(); return; }
    } catch (e) {}
    setTimeout(tick, 400);
  };
  tick();
})();"""


def inject_livereload_into_html(dst: Path) -> None:
    """Insert a script tag for ``/__ryact_livereload.js`` into *dst* (typically copied HTML)."""
    if not dst.is_file():
        return
    raw = dst.read_text(encoding="utf8")
    if "__ryact_livereload.js" in raw:
        return
    tag = '<script src="/__ryact_livereload.js"></script>'
    lower = raw.lower()
    idx = lower.rfind("</body>")
    new = raw[:idx] + "\n    " + tag + "\n" + raw[idx:] if idx != -1 else raw.rstrip() + "\n" + tag + "\n"
    dst.write_text(new, encoding="utf8")


class LiveReloadCounter:
    """Increments on successful rebuilds (exit code 0) for browser polling."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.version = 0

    def on_rebuild(self, rc: int) -> None:
        if rc != 0:
            return
        with self._lock:
            self.version += 1


def _make_handler(
    out_dir: Path,
    live: LiveReloadCounter | None,
) -> type[SimpleHTTPRequestHandler]:
    out_s = str(out_dir.resolve())

    class DevHandler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):  # noqa: ANN002
            super().__init__(*args, directory=out_s, **kwargs)

        def log_message(self, format: str, *args: object) -> None:
            return

        def do_GET(self) -> None:  # noqa: N802
            path = urlparse(self.path).path
            if live is not None and path == "/__ryact_livereload.js":
                body = LIVERELOAD_JS.encode("utf8")
                self.send_response(200)
                self.send_header("Content-Type", "application/javascript; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            if live is not None and path == "/__ryact_livereload":
                payload = json.dumps({"v": live.version}).encode("utf8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
                return
            super().do_GET()

    return DevHandler


def start_dev_server(
    *,
    out_dir: Path,
    host: str,
    port: int,
    livereload: LiveReloadCounter | None,
    on_bound: Callable[[], None] | None = None,
) -> tuple[HTTPServer, threading.Thread]:
    """Start ``HTTPServer`` in a daemon thread; returns *(server, thread)*."""

    handler_cls = _make_handler(out_dir, livereload)
    server = HTTPServer((host, port), handler_cls)
    server.allow_reuse_address = True

    def run() -> None:
        if on_bound is not None:
            on_bound()
        server.serve_forever()

    th = threading.Thread(target=run, name="ryact-vite-dev-http", daemon=True)
    th.start()
    return server, th
