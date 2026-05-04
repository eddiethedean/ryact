from __future__ import annotations

from pathlib import Path

from ryact_build.pyx_step import compile_pyx_file


def test_compile_pyx_file_module(tmp_path: Path) -> None:
    src = tmp_path / "a.pyx"
    src.write_text('<div id="root">hello</div>\n', encoding="utf8")
    out = tmp_path / "out.py"
    compile_pyx_file(input_path=src, output_path=out, mode="module")
    text = out.read_text(encoding="utf8")
    assert "def render" in text
    assert "from ryact import" in text
    assert "hello" in text
