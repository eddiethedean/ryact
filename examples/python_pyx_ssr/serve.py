#!/usr/bin/env python3
"""Minimal HTTP server: GET / is SSR from PYX-compiled ``render``; /static/* serves files."""

from __future__ import annotations

import argparse
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from ryact_dom import render_to_string

from app.page_gen import render

ROOT = Path(__file__).resolve().parent
STATIC = ROOT / "static"
DIST_STATIC = ROOT / "dist" / "static"

DOC = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Python PYX Ryact</title>
  <link rel="stylesheet" href="/static/styles.css" />
</head>
<body>
{inner}
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        return

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        if path == "/":
            inner = render_to_string(render({}))
            html = DOC.format(inner=inner).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(html)))
            self.end_headers()
            self.wfile.write(html)
            return

        if path.startswith("/static/"):
            rel = path[len("/static/") :].lstrip("/")
            if ".." in rel.split("/"):
                self.send_error(400)
                return
            for base in (DIST_STATIC, STATIC):
                candidate = (base / rel).resolve()
                try:
                    candidate.relative_to(base.resolve())
                except ValueError:
                    continue
                if candidate.is_file():
                    data = candidate.read_bytes()
                    ctype = "application/octet-stream"
                    if candidate.suffix == ".css":
                        ctype = "text/css; charset=utf-8"
                    self.send_response(200)
                    self.send_header("Content-Type", ctype)
                    self.send_header("Content-Length", str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
                    return

        self.send_error(404)


def main() -> int:
    parser = argparse.ArgumentParser(description="Serve PYX → Python Ryact SSR app.")
    parser.add_argument("--host", default=os.environ.get("RYACT_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("RYACT_PORT", "8766")))
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    host, port = server.server_address[0], server.server_address[1]
    print(f"python_pyx_ssr: http://{host}:{port}/  (Ctrl+C to stop)", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("", flush=True)
        return 130
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
