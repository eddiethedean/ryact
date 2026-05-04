from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any, cast

import pytest
from ryact_dom import create_root
from ryact_dom.dom import Container

from scripts.jsx_run import dom_to_html
from scripts.jsx_to_py import eval_compiled


def _build(tmp_path: Path, *, entry: Path) -> Path:
    out_py = tmp_path / "app.py"
    out_map = tmp_path / "app.map.json"
    try:
        subprocess.run(
            [
                "node",
                "scripts/jsx_build.mjs",
                str(entry),
                "--out",
                str(out_py),
                "--map",
                str(out_map),
            ],
            cwd=Path(__file__).parents[1],
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        pytest.skip("node is not installed; skipping jsx tooling integration tests")
    except subprocess.CalledProcessError as e:
        if isinstance(e.stderr, str) and (
            "ERR_MODULE_NOT_FOUND" in e.stderr or "Cannot find package" in e.stderr
        ):
            pytest.skip(
                "jsx build dependencies are missing; skipping jsx tooling integration tests"
            )
        raise
    assert out_py.exists()
    assert out_map.exists()
    return out_py


def test_jsx_tooling_build_and_dom_render(tmp_path: Path) -> None:
    repo_root = Path(__file__).parents[1]
    entry = repo_root / "tests_jsx" / "fixtures" / "app_main_ok.tsx"
    mod = _build(tmp_path, entry=entry)

    element = eval_compiled(mod.read_text(encoding="utf8"), scope={})
    container = Container()
    root = create_root(container)
    root.render(cast(Any, element))

    assert dom_to_html(container) == '<div id="app">ok</div>'


def test_jsx_tooling_error_reports_tsx_location(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo_root = Path(__file__).parents[1]
    entry = repo_root / "tests_jsx" / "fixtures" / "app_main_throws.tsx"
    mod = _build(tmp_path, entry=entry)

    # Simulate runner behavior: exec module, then evaluate (will NameError on `boom`).
    code = mod.read_text(encoding="utf8")
    g: dict[str, object] = {}
    loc: dict[str, object] = {}
    exec(code, g, loc)

    with pytest.raises(NameError):
        eval_compiled(code, scope={})

    # Best-effort: mapping exists in module globals, so the runner prints a hint.
    from scripts.jsx_run import _format_tsx_loc

    hint = _format_tsx_loc({**g, **loc})
    assert hint is not None
    assert "tests_jsx/fixtures/app_main_throws.tsx" in hint
