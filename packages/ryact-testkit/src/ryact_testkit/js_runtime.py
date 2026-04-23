"""
Optional JavaScript execution via `js2py` (install `ryact-testkit[javascript]`).

Use this when translating or cross-checking upstream React tests that embed JS snippets.
"""

from __future__ import annotations

from typing import Any


def is_javascript_runtime_available() -> bool:
    try:
        import js2py  # noqa: F401
    except ImportError:
        return False
    return True


def _require_js2py() -> Any:
    try:
        import js2py
    except ImportError as e:
        raise ImportError(
            "Running JavaScript requires js2py. Install with:\n"
            "  pip install 'ryact-testkit[javascript]'\n"
            "or:\n"
            "  pip install js2py"
        ) from e
    return js2py


def eval_js(source: str) -> Any:
    """
    Evaluate a JavaScript expression or program and return the last evaluated value.

    For multi-statement scripts, prefer :class:`JsContext` so variables persist.
    """
    js2py = _require_js2py()
    return js2py.eval_js(source)


class JsContext:
    """
    Persistent JS scope (wraps ``js2py.EvalJs``).

    Example::

        ctx = JsContext()
        ctx.execute(\"var x = 1;\")
        assert ctx.eval(\"x + 1\") == 2
    """

    def __init__(self) -> None:
        js2py = _require_js2py()
        self._ctx = js2py.EvalJs()

    def execute(self, source: str) -> None:
        """Run a script for side effects (assignments, function declarations, etc.)."""
        self._ctx.execute(source)

    def eval(self, expr: str) -> Any:
        """Evaluate an expression in the current scope and return the result."""
        return self._ctx.eval(expr)
