from __future__ import annotations

import stat
from pathlib import Path

import pytest
from ryact_build.bundle_config import BundleConfig, bundle_argv
from ryact_build.esbuild import build_esbuild_argv, local_esbuild_bin
from ryact_build.exceptions import EsbuildNotFoundError


def test_local_esbuild_bin_finds_unix_shim(tmp_path: Path) -> None:
    bin_dir = tmp_path / "node_modules" / ".bin"
    bin_dir.mkdir(parents=True)
    script = bin_dir / "esbuild"
    script.write_text("#!/usr/bin/env node\n", encoding="utf8")
    script.chmod(script.stat().st_mode | stat.S_IXUSR)
    found = local_esbuild_bin(tmp_path)
    assert found == script


def test_build_esbuild_argv_prefers_local(tmp_path: Path) -> None:
    bin_dir = tmp_path / "node_modules" / ".bin"
    bin_dir.mkdir(parents=True)
    script = bin_dir / "esbuild"
    script.write_text("#!/usr/bin/env node\n", encoding="utf8")
    script.chmod(script.stat().st_mode | stat.S_IXUSR)
    argv = build_esbuild_argv(tmp_path, ["--version"])
    assert argv[0] == str(script)
    assert argv[1:] == ["--version"]


def test_build_esbuild_argv_falls_back_to_npx(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_which(name: str) -> str | None:
        if name == "npx":
            return "/usr/bin/npx"
        return None

    monkeypatch.setattr("ryact_build.esbuild.shutil.which", fake_which)
    argv = build_esbuild_argv(tmp_path, ["--version"])
    assert argv == ["/usr/bin/npx", "--yes", "esbuild", "--version"]


def test_build_esbuild_argv_raises_without_npx(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("ryact_build.esbuild.shutil.which", lambda _name: None)
    with pytest.raises(EsbuildNotFoundError):
        build_esbuild_argv(tmp_path, ["--version"])


def test_bundle_argv_minify_and_extra(tmp_path: Path) -> None:
    entry = tmp_path / "app.tsx"
    entry.write_text("export {}\n", encoding="utf8")
    out = tmp_path / "dist"
    cfg = BundleConfig(
        entry=entry,
        out_dir=out,
        minify=True,
        extra=("--log-limit=0",),
    )
    argv = bundle_argv(cfg)
    assert "--minify" in argv
    assert "--log-limit=0" in argv
    assert argv[0] == str(entry)
    assert "--format=esm" in argv


def test_bundle_argv_define_inject_watch(tmp_path: Path) -> None:
    entry = tmp_path / "e.ts"
    entry.write_text("x", encoding="utf8")
    inj = tmp_path / "shim.js"
    inj.write_text("{}", encoding="utf8")
    cfg = BundleConfig(
        entry=entry,
        out_dir=tmp_path / "out",
        defines=(("DEBUG", "false"), ("A", "1")),
        injects=(inj,),
        watch=True,
    )
    argv = bundle_argv(cfg)
    assert "--watch" in argv
    assert "--inject:" + str(inj) in argv
    assert "--define:A=1" in argv
    assert "--define:DEBUG=false" in argv
