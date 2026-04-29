from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from ryact.element import Element
from ryact_testkit import create_noop_root

from scripts.jsx_to_py import eval_compiled


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
    out_py = tmp_path / (entry.stem + ".py")
    try:
        subprocess.run(
            ["node", "scripts/jsx_build.mjs", str(entry), "--out", str(out_py)],
            cwd=repo_root(),
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        import pytest

        pytest.skip("node is not installed; skipping TSX parity tests")
    except subprocess.CalledProcessError as e:
        import pytest

        if isinstance(e.stderr, str) and (
            "ERR_MODULE_NOT_FOUND" in e.stderr or "Cannot find package" in e.stderr
        ):
            pytest.skip("jsx build dependencies are missing; skipping TSX parity tests")
        raise
    return out_py


def eval_render_module(module_path: Path, *, scope: dict[str, object]) -> object:
    code = module_path.read_text(encoding="utf8")
    return eval_compiled(code, scope=scope)


def render_noop_sessioned(session: NoopSession, element: object) -> NoopResult:
    return session.render(element)


def assert_equivalent(a: NoopResult, b: NoopResult) -> None:
    assert a.snapshot == b.snapshot
    assert a.ops == b.ops
