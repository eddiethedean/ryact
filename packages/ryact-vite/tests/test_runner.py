from __future__ import annotations

import stat
from pathlib import Path

import pytest
from ryact_vite.exceptions import ViteNotFoundError
from ryact_vite.runner import build_vite_argv, local_vite_bin


def test_local_vite_bin_finds_unix_shim(tmp_path: Path) -> None:
    bin_dir = tmp_path / "node_modules" / ".bin"
    bin_dir.mkdir(parents=True)
    script = bin_dir / "vite"
    script.write_text("#!/usr/bin/env node\n", encoding="utf8")
    script.chmod(script.stat().st_mode | stat.S_IXUSR)
    found = local_vite_bin(tmp_path)
    assert found == script


def test_build_vite_argv_prefers_local(tmp_path: Path) -> None:
    bin_dir = tmp_path / "node_modules" / ".bin"
    bin_dir.mkdir(parents=True)
    script = bin_dir / "vite"
    script.write_text("#!/usr/bin/env node\n", encoding="utf8")
    script.chmod(script.stat().st_mode | stat.S_IXUSR)
    argv = build_vite_argv(tmp_path, ["build", "--emptyOutDir"])
    assert argv[0] == str(script)
    assert argv[1:] == ["build", "--emptyOutDir"]


def test_build_vite_argv_falls_back_to_npx(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_which(name: str) -> str | None:
        if name == "npx":
            return "/usr/bin/npx"
        return None

    monkeypatch.setattr("ryact_vite.runner.shutil.which", fake_which)
    argv = build_vite_argv(tmp_path, ["build"])
    assert argv == ["/usr/bin/npx", "--yes", "vite", "build"]


def test_build_vite_argv_raises_without_npx(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("ryact_vite.runner.shutil.which", lambda _name: None)
    with pytest.raises(ViteNotFoundError):
        build_vite_argv(tmp_path, ["build"])


def test_init_config_template_readable() -> None:
    from ryact_vite.cli import _template_vite_config_text

    text = _template_vite_config_text()
    assert "defineConfig" in text
    assert "vite" in text
