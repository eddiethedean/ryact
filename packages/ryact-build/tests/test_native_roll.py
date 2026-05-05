from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from ryact_build import native_roll
from ryact_build.bundle_config import BundleConfig
from ryact_build.exceptions import NativeExtensionUnavailableError


def test_load_native_module_missing_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail() -> None:
        raise NativeExtensionUnavailableError("test")

    monkeypatch.setattr(native_roll, "_load_native_module", fail)
    cfg = BundleConfig(entry=Path("e.ts"), out_dir=Path("out"))
    with pytest.raises(NativeExtensionUnavailableError):
        native_roll.run_bundle_roll_from_config(config=cfg, cwd=Path("."), verbose=False)


def test_run_bundle_roll_calls_native(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    mock_native = MagicMock()
    monkeypatch.setattr(native_roll, "_load_native_module", lambda: mock_native)

    entry = tmp_path / "e.ts"
    out = tmp_path / "out"
    entry.write_text("export const x = 1;\n", encoding="utf8")
    out.mkdir()
    cfg = BundleConfig(entry=entry, out_dir=out)
    rc = native_roll.run_bundle_roll_from_config(config=cfg, cwd=tmp_path, verbose=False)
    assert rc == 0
    mock_native.bundle_roll.assert_called_once()


def test_bundle_roll_failure_returns_one(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    mock_native = MagicMock()
    mock_native.bundle_roll.side_effect = RuntimeError("boom")
    monkeypatch.setattr(native_roll, "_load_native_module", lambda: mock_native)

    entry = tmp_path / "e.ts"
    out = tmp_path / "out"
    entry.write_text("export const x = 1;\n", encoding="utf8")
    out.mkdir()
    cfg = BundleConfig(entry=entry, out_dir=out)
    rc = native_roll.run_bundle_roll_from_config(config=cfg, cwd=tmp_path, verbose=False)
    assert rc == 1
