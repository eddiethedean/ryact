from __future__ import annotations

from pathlib import Path

from scripts.jsx_to_py import jsx_to_python


def test_jsx_codegen_golden_expr() -> None:
    # This test requires a working Node.js runtime to execute the TSX->Python transform.
    # Skip gracefully when `node` is not available in the environment.
    import shutil

    import pytest

    if shutil.which("node") is None:
        pytest.skip("node is not installed; skipping jsx codegen golden tests")

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
        try:
            got = jsx_to_python(path=src, mode="expr").code
        except Exception as e:
            # When the Node transform's dependencies are not installed, Node will fail with
            # module resolution errors (ERR_MODULE_NOT_FOUND). Skip instead of failing the
            # Python test suite.
            import subprocess

            msg = str(e)
            stderr = ""
            if isinstance(e, subprocess.CalledProcessError) and isinstance(e.stderr, str):
                stderr = e.stderr
            if (
                "ERR_MODULE_NOT_FOUND" in msg
                or "Cannot find package" in msg
                or "ERR_MODULE_NOT_FOUND" in stderr
                or "Cannot find package" in stderr
            ):
                pytest.skip("jsx transform dependencies are missing; skipping jsx codegen tests")
            raise
        expected = expected_path.read_text(encoding="utf8")
        assert got == expected
