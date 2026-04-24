from __future__ import annotations

from pathlib import Path

from ryact_pyx import compile_pyx_to_python

_HERE = Path(__file__).parent
_FIXTURES = _HERE / "fixtures"
_GOLDEN = _HERE / "golden"


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def test_golden_fixtures() -> None:
    for fixture in sorted(_FIXTURES.glob("*.pyx")):
        name = fixture.stem
        expected = _read(_GOLDEN / f"{name}.py.txt")
        got = compile_pyx_to_python(_read(fixture), mode="expr")
        assert got == expected
