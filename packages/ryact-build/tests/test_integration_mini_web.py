from __future__ import annotations

import shutil
from pathlib import Path

from ryact_build.cli import main

_REPO_ROOT = Path(__file__).resolve().parents[3]
_MINI = _REPO_ROOT / "packages" / "ryact-build" / "tests" / "fixtures" / "mini_web"


def test_bundle_mini_web_fixture_smoke() -> None:
    dist = _MINI / "dist"
    if dist.is_dir():
        shutil.rmtree(dist)

    entry = _MINI / "src" / "entry.ts"
    html = _MINI / "index.html"
    rc = main(
        [
            "bundle",
            "--cwd",
            str(_REPO_ROOT),
            "--entry",
            str(entry),
            "--out-dir",
            str(dist),
            "--html",
            str(html),
            "--clean",
        ]
    )
    assert rc == 0
    assert (dist / "entry.js").is_file()
    assert (dist / "index.html").is_file()
    assert "answer" in (dist / "entry.js").read_text(encoding="utf8")
