from __future__ import annotations

from pathlib import Path

import pytest
from ryact_vite.config import load_config
from ryact_vite.runner import argv_bundle, parse_preview_port, run_ryact_build


def test_parse_preview_port() -> None:
    rest, port = parse_preview_port(["--port", "9000"], default=4173)
    assert port == 9000
    assert rest == []
    rest2, port2 = parse_preview_port(["--", "-p", "3000", "extra"], default=1)
    assert port2 == 3000
    assert rest2 == ["--", "extra"]


def test_argv_bundle_uses_config_defaults(tmp_path: Path) -> None:
    cfg = {"entry": "src/main.ts", "outDir": "dist", "format": "iife"}
    argv = argv_bundle(
        cwd=tmp_path,
        config=cfg,
        entry=None,
        out_dir=None,
        fmt=None,
        target=None,
        define=None,
        inject=None,
        html=None,
        assets=None,
        minify=False,
        clean=False,
        verbose=False,
        watch=False,
    )
    assert argv[0] == "bundle"
    assert "--entry" in argv
    assert "src/main.ts" in argv
    assert "--out-dir" in argv
    assert "dist" in argv
    assert "--format" in argv
    assert "iife" in argv


def test_argv_bundle_watch(tmp_path: Path) -> None:
    argv = argv_bundle(
        cwd=tmp_path,
        config={},
        entry=Path("e.ts"),
        out_dir=Path("out"),
        fmt=None,
        target=None,
        define=None,
        inject=None,
        html=None,
        assets=None,
        minify=False,
        clean=False,
        verbose=False,
        watch=True,
    )
    assert argv[0] == "watch"


def test_load_config_empty_missing(tmp_path: Path) -> None:
    assert load_config(tmp_path) == {}


def test_run_ryact_build_smoke(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[list[str]] = []

    def fake_main(argv: list[str]) -> int:
        seen.append(list(argv))
        return 0

    monkeypatch.setattr("ryact_build.cli.main", fake_main)
    rc = run_ryact_build(["bundle", "--help"])
    assert rc == 0
    assert seen == [["bundle", "--help"]]
