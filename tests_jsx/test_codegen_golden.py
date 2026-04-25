from __future__ import annotations

from pathlib import Path

from scripts.jsx_to_py import jsx_to_python


def test_jsx_codegen_golden_expr() -> None:
    root = Path(__file__).parent
    fixtures = root / "fixtures"
    golden = root / "golden"

    cases = [
        ("basic_host", fixtures / "basic_host.tsx", golden / "basic_host.py.txt"),
        (
            "exprs_and_components",
            fixtures / "exprs_and_components.tsx",
            golden / "exprs_and_components.py.txt",
        ),
        ("fragment", fixtures / "fragment.tsx", golden / "fragment.py.txt"),
        ("wrappers_exprs", fixtures / "wrappers_exprs.tsx", golden / "wrappers_exprs.py.txt"),
    ]

    for _name, src, expected_path in cases:
        got = jsx_to_python(path=src, mode="expr").code
        expected = expected_path.read_text(encoding="utf8")
        assert got == expected
