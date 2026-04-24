from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal, cast

from .ast import Element, Expr, Node, Root, Text
from .parser import parse_pyx


@dataclass(frozen=True)
class CompileOptions:
    h_name: str = "h"
    scope_name: str = "scope"


def compile_pyx_to_python(source: str, *, mode: Literal["expr", "module"] = "expr") -> str:
    ast = parse_pyx(source)
    opts = CompileOptions()
    expr = _emit_node(ast, opts=opts)
    if mode == "expr":
        return expr + "\n"
    if mode == "module":
        return (
            "from __future__ import annotations\n\n"
            "from ryact import Fragment, h\n\n"
            f"def render({opts.scope_name}: dict[str, object]) -> object:\n"
            f"    return {expr}\n"
        )
    raise ValueError(f"Unsupported mode: {mode!r}")


def eval_compiled(code: str, scope: dict[str, object] | None = None) -> object:
    """
    Evaluate compiled code (for tests).

    If code is a module (contains render()), calls render(scope).
    Otherwise, evaluates it as an expression.
    """
    g: dict[str, object] = {"__builtins__": __builtins__}  # type: ignore[assignment]
    ryact = __import__("ryact")
    g["h"] = ryact.h  # type: ignore[attr-defined]
    g["Fragment"] = ryact.Fragment  # type: ignore[attr-defined]
    loc: dict[str, object] = {}
    if scope is None:
        scope = {}
    loc["scope"] = scope
    if "def render" in code:
        exec(code, g, loc)
        fn = loc.get("render")
        assert callable(fn)
        render = cast(Callable[[dict[str, object]], object], fn)
        return render(scope)
    return eval(code, g, loc)


def _emit_node(node: Node, *, opts: CompileOptions) -> str:
    if isinstance(node, Root):
        child_exprs = [_emit_node(c, opts=opts) for c in node.children]
        child_exprs = [c for c in child_exprs if c != "None"]
        if not child_exprs:
            return "None"
        return f"{opts.h_name}(Fragment, None, " + ", ".join(child_exprs) + ")"
    if isinstance(node, Text):
        s = node.value
        # Normalize text: strip if it's purely whitespace between tags.
        if s.strip() == "":
            return "None"
        return repr(s)
    if isinstance(node, Expr):
        return f"({node.source})"
    if isinstance(node, Element):
        tag_expr = _emit_tag(node.tag, opts=opts)
        props_expr = _emit_props(node.attrs, opts=opts)
        child_exprs = [_emit_node(c, opts=opts) for c in node.children]
        child_exprs = [c for c in child_exprs if c != "None"]
        args = ", ".join([tag_expr, props_expr, *child_exprs])
        return f"{opts.h_name}({args})"
    raise TypeError(f"Unsupported node: {type(node)!r}")


def _emit_tag(tag: str, *, opts: CompileOptions) -> str:
    # Component tags resolve from an explicit scope mapping.
    if tag and tag[0].isupper():
        return f"{opts.scope_name}[{tag!r}]"
    return repr(tag)


def _emit_props(attrs: dict[str, Any], *, opts: CompileOptions) -> str:
    if not attrs:
        return "None"
    items: list[str] = []
    for k, v in attrs.items():
        if isinstance(v, Expr):
            items.append(f"{k!r}: ({v.source})")
        else:
            items.append(f"{k!r}: {repr(v)}")
    return "{" + ", ".join(items) + "}"
