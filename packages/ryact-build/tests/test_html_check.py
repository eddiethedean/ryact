from __future__ import annotations

from pathlib import Path

from ryact_build.html_check import warn_missing_script_refs


def test_warn_missing_script_relative(tmp_path: Path, capsys) -> None:
    dist = tmp_path / "dist"
    dist.mkdir()
    html = dist / "index.html"
    html.write_text('<script type="module" src="./main.js"></script>', encoding="utf8")
    warn_missing_script_refs(html_path=html, out_dir=dist)
    err = capsys.readouterr().err
    assert "missing script asset" in err
    assert "main.js" in err


def test_warn_resolves_existing(tmp_path: Path, capsys) -> None:
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "main.js").write_text("", encoding="utf8")
    html = dist / "index.html"
    html.write_text('<script src="./main.js"></script>', encoding="utf8")
    warn_missing_script_refs(html_path=html, out_dir=dist)
    assert capsys.readouterr().err == ""


def test_skips_http_and_absolute(tmp_path: Path, capsys) -> None:
    dist = tmp_path / "dist"
    dist.mkdir()
    html = dist / "index.html"
    html.write_text(
        '<script src="https://x/y.js"></script><script src="/abs.js"></script>',
        encoding="utf8",
    )
    warn_missing_script_refs(html_path=html, out_dir=dist)
    assert capsys.readouterr().err == ""
