from __future__ import annotations

import re
import sys
from pathlib import Path

# Relative script src only (no scheme). Groups single-quoted, double-quoted, unquoted.
_SCRIPT_SRC = re.compile(
    r"""<script\b[^>]*\bsrc\s*=\s*(?:["']([^"']+)["']|([^\s>]+))""",
    re.IGNORECASE | re.DOTALL,
)


def warn_missing_script_refs(*, html_path: Path, out_dir: Path) -> None:
    """
    After copying HTML into ``out_dir``, warn on stderr if any **relative**
    ``<script src=...>`` does not resolve to an existing file under ``out_dir``.
    Skips ``http:``, ``https:``, ``//``, and ``data:`` URLs.
    """
    text = html_path.read_text(encoding="utf8")
    out_dir = out_dir.resolve()
    for m in _SCRIPT_SRC.finditer(text):
        raw = (m.group(1) or m.group(2) or "").strip()
        if not raw or raw.startswith(("#", "javascript:")):
            continue
        lower = raw.lower()
        if lower.startswith("http:") or lower.startswith("https:") or lower.startswith("//"):
            continue
        if lower.startswith("data:"):
            continue
        # ignore query strings for existence check
        path_part = raw.split("?", 1)[0]
        if path_part.startswith("/"):
            # Absolute URL path; skip (different deploy layouts).
            continue
        candidate = (out_dir / path_part).resolve()
        try:
            candidate.relative_to(out_dir)
        except ValueError:
            print(
                f"ryact-build: warning: script src {raw!r} resolves outside out-dir; skipping check",
                file=sys.stderr,
            )
            continue
        if not candidate.is_file():
            print(
                f"ryact-build: warning: missing script asset (chunks may explain this): "
                f"{raw!r} -> expected {candidate}",
                file=sys.stderr,
            )
