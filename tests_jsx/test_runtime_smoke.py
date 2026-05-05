from __future__ import annotations

from pathlib import Path

from ryact import Fragment, create_element, h

from scripts.jsx_to_py import eval_compiled, jsx_to_python, try_resolve_ryact_jsx_binary


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_runtime_smoke_basic_host_tree() -> None:
    import pytest

    if try_resolve_ryact_jsx_binary(_repo_root()) is None:
        pytest.skip("ryact-jsx not available; skipping jsx runtime smoke tests")
    root = Path(__file__).parent
    src = root / "fixtures" / "basic_host.tsx"
    code = jsx_to_python(path=src, mode="expr").code
    got = eval_compiled(code, scope={})
    expected = h("div", {"id": "x"}, "hello")
    assert got == expected


def test_runtime_smoke_component_and_expr_scope() -> None:
    import pytest

    if try_resolve_ryact_jsx_binary(_repo_root()) is None:
        pytest.skip("ryact-jsx not available; skipping jsx runtime smoke tests")
    root = Path(__file__).parent
    src = root / "fixtures" / "exprs_and_components.tsx"
    code = jsx_to_python(path=src, mode="expr").code

    def Button(**props: object) -> object:
        return create_element("button", dict(props))

    got = eval_compiled(code, scope={"Button": Button, "flag": True, "n": 3})
    expected = h(Button, {"disabled": True, "count": 3})
    assert got == expected


def test_runtime_smoke_fragment() -> None:
    import pytest

    if try_resolve_ryact_jsx_binary(_repo_root()) is None:
        pytest.skip("ryact-jsx not available; skipping jsx runtime smoke tests")
    root = Path(__file__).parent
    src = root / "fixtures" / "fragment.tsx"
    code = jsx_to_python(path=src, mode="expr").code

    got = eval_compiled(code, scope={"n": 7})
    expected = h(Fragment, None, "a", "b", h("div", None), 7)
    assert got == expected
