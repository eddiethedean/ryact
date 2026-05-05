from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import pytest
from ryact.element import Element
from ryact_testkit import create_noop_root

from scripts.jsx_to_py import eval_compiled, try_resolve_ryact_jsx_binary


@dataclass(frozen=True)
class NoopResult:
    snapshot: Any
    ops: list[dict[str, Any]]


@dataclass
class NoopSession:
    """
    Stateful no-op host session to support interactions.
    """

    root: Any

    @classmethod
    def create(cls) -> NoopSession:
        return cls(root=create_noop_root())

    def render(self, element: object) -> NoopResult:
        self.root.render(cast(Element | None, element))
        return NoopResult(snapshot=self.root.container.last_committed, ops=self.root.get_ops())

    def clear_ops(self) -> None:
        self.root.clear_ops()


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def compile_tsx_to_module(tmp_path: Path, *, entry: Path) -> Path:
    root = repo_root()
    if try_resolve_ryact_jsx_binary(root) is None:
        pytest.skip(
            "ryact-jsx not available (build packages/ryact-jsx or set RYACT_JSX_TO_PY)"
        )

    out_py = tmp_path / (entry.stem + ".py")
    try:
        subprocess.run(
            [sys.executable, str(root / "scripts" / "jsx_build.py"), str(entry), "--out", str(out_py)],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(e.stderr or e.stdout or "jsx_build.py failed") from e
    return out_py


def eval_render_module(module_path: Path, *, scope: dict[str, object]) -> object:
    code = module_path.read_text(encoding="utf8")
    return eval_compiled(code, scope=scope)


def render_noop_sessioned(session: NoopSession, element: object) -> NoopResult:
    return session.render(element)


def assert_equivalent(a: NoopResult, b: NoopResult) -> None:
    assert a.snapshot == b.snapshot
    assert a.ops == b.ops
