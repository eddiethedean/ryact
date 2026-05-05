from __future__ import annotations

import json
from pathlib import Path
from typing import Any

CONFIG_FILENAME = "ryact-vite.json"


def load_config(cwd: Path) -> dict[str, Any]:
    """Load optional ``ryact-vite.json`` from *cwd* (may be empty)."""
    path = cwd / CONFIG_FILENAME
    if not path.is_file():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf8"))
    except json.JSONDecodeError as e:
        raise ValueError(f"invalid JSON in {path}: {e}") from e
    if not isinstance(raw, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return raw


def default_config_template() -> dict[str, Any]:
    return {
        "entry": "src/main.ts",
        "outDir": "dist",
        "html": "index.html",
        "minify": False,
        "clean": False,
        "verbose": False,
        "format": "esm",
        "devPort": 5173,
        "devHost": "127.0.0.1",
        "livereload": True,
    }
