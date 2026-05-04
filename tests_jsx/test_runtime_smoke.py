from __future__ import annotations

from pathlib import Path

from ryact import Fragment, create_element, h

from scripts.jsx_to_py import eval_compiled, jsx_to_python


def test_runtime_smoke_basic_host_tree() -> None:
    import shutil

    import pytest

    if shutil.which("node") is None:
        pytest.skip("node is not installed; skipping jsx runtime smoke tests")
    root = Path(__file__).parent
    src = root / "fixtures" / "basic_host.tsx"
    try:
        code = jsx_to_python(path=src, mode="expr").code
    except Exception as e:
        import subprocess

        if (
            isinstance(e, subprocess.CalledProcessError)
            and isinstance(e.stderr, str)
            and ("ERR_MODULE_NOT_FOUND" in e.stderr or "Cannot find package" in e.stderr)
        ):
            pytest.skip("jsx transform dependencies are missing; skipping jsx runtime smoke")
        raise
    got = eval_compiled(code, scope={})
    expected = h("div", {"id": "x"}, "hello")
    assert got == expected


def test_runtime_smoke_component_and_expr_scope() -> None:
    import shutil

    import pytest

    if shutil.which("node") is None:
        pytest.skip("node is not installed; skipping jsx runtime smoke tests")
    root = Path(__file__).parent
    src = root / "fixtures" / "exprs_and_components.tsx"
    try:
        code = jsx_to_python(path=src, mode="expr").code
    except Exception as e:
        import subprocess

        if (
            isinstance(e, subprocess.CalledProcessError)
            and isinstance(e.stderr, str)
            and ("ERR_MODULE_NOT_FOUND" in e.stderr or "Cannot find package" in e.stderr)
        ):
            pytest.skip("jsx transform dependencies are missing; skipping jsx runtime smoke")
        raise

    def Button(**props: object) -> object:
        return create_element("button", dict(props))

    got = eval_compiled(code, scope={"Button": Button, "flag": True, "n": 3})
    expected = h(Button, {"disabled": True, "count": 3})
    assert got == expected


def test_runtime_smoke_fragment() -> None:
    import shutil

    import pytest

    if shutil.which("node") is None:
        pytest.skip("node is not installed; skipping jsx runtime smoke tests")
    root = Path(__file__).parent
    src = root / "fixtures" / "fragment.tsx"
    try:
        code = jsx_to_python(path=src, mode="expr").code
    except Exception as e:
        import subprocess

        if (
            isinstance(e, subprocess.CalledProcessError)
            and isinstance(e.stderr, str)
            and ("ERR_MODULE_NOT_FOUND" in e.stderr or "Cannot find package" in e.stderr)
        ):
            pytest.skip("jsx transform dependencies are missing; skipping jsx runtime smoke")
        raise

    got = eval_compiled(code, scope={"n": 7})
    expected = h(Fragment, None, "a", "b", h("div", None), 7)
    assert got == expected
