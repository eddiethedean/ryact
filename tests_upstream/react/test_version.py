from __future__ import annotations

import tomllib
from pathlib import Path

from ryact import __version__


def test_reactversion_matches_package_json() -> None:
    # Upstream: ReactVersion-test.js
    # "ReactVersion matches package.json"
    repo = Path(__file__).resolve().parents[2]
    pyproject = repo / "packages" / "ryact" / "pyproject.toml"
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    assert __version__ == data["project"]["version"]

