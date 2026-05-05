from __future__ import annotations

import json
from pathlib import Path

import pytest
from ryact_vite.cli import _template_config_text, main


def test_init_config_template_is_json() -> None:
    text = _template_config_text()
    data = json.loads(text)
    assert "entry" in data
    assert "outDir" in data


def test_main_init_config_writes_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    rc = main(["init-config"])
    assert rc == 0
    p = tmp_path / "ryact-vite.json"
    assert p.is_file()
    assert json.loads(p.read_text(encoding="utf8"))["outDir"] == "dist"


def test_main_build_invokes_ryact_build(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[list[str]] = []

    def fake_run(argv: list[str]) -> int:
        calls.append(list(argv))
        return 0

    monkeypatch.setattr("ryact_vite.cli.run_ryact_build", fake_run)
    monkeypatch.chdir(tmp_path)
    (tmp_path / "ryact-vite.json").write_text(
        json.dumps({"entry": "src/x.ts", "outDir": "dist"}),
        encoding="utf8",
    )
    rc = main(["build"])
    assert rc == 0
    assert len(calls) == 1
    assert calls[0][0] == "bundle"
    assert "--entry" in calls[0]
