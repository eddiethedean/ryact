from __future__ import annotations

from pathlib import Path
from typing import Literal

from ryact_pyx import compile_pyx_to_python  # type: ignore[import-untyped]


def compile_pyx_file(
    *,
    input_path: Path,
    output_path: Path,
    mode: Literal["expr", "module"] = "module",
) -> None:
    """Read ``.pyx``, compile to Python, write ``output_path``."""
    source = input_path.read_text(encoding="utf8")
    code = compile_pyx_to_python(source, mode=mode)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(code, encoding="utf8")
