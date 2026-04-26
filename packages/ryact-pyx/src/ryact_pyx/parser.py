from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .ast import Element, Expr, Node, Root, Text


class ParseError(ValueError):
    pass


@dataclass
class _Cursor:
    s: str
    i: int = 0

    def eof(self) -> bool:
        return self.i >= len(self.s)

    def peek(self) -> str:
        return self.s[self.i] if not self.eof() else ""

    def consume(self, expected: str) -> None:
        if not self.s.startswith(expected, self.i):
            raise ParseError(f"Expected {expected!r} at {self.i}")
        self.i += len(expected)

    def skip_ws(self) -> None:
        while not self.eof() and self.s[self.i].isspace():
            self.i += 1


def parse_pyx(source: str) -> Node:
    c = _Cursor(source)
    nodes: list[Node] = []
    while True:
        c.skip_ws()
        if c.eof():
            break
        nodes.append(_parse_node(c))
    if not nodes:
        return Text("")
    if len(nodes) == 1:
        return nodes[0]
    return Root(children=nodes)


def _parse_node(c: _Cursor) -> Node:
    if c.peek() == "<":
        return _parse_element(c)
    if c.peek() == "{":
        return _parse_expr(c)
    return _parse_text_until(c, stop_chars={"<", "{"})


def _parse_text_until(c: _Cursor, *, stop_chars: set[str]) -> Text:
    start = c.i
    while not c.eof() and c.peek() not in stop_chars:
        c.i += 1
    return Text(c.s[start : c.i])


def _parse_ident(c: _Cursor) -> str:
    start = c.i
    if c.eof() or not (c.peek().isalpha() or c.peek() == "_"):
        raise ParseError(f"Expected identifier at {c.i}")
    c.i += 1
    while not c.eof() and (c.peek().isalnum() or c.peek() in ("_", "-", ":")):
        c.i += 1
    return c.s[start : c.i]


def _parse_quoted(c: _Cursor) -> str:
    quote = c.peek()
    if quote not in ("'", '"'):
        raise ParseError(f"Expected quote at {c.i}")
    c.i += 1
    out: list[str] = []
    while not c.eof():
        ch = c.peek()
        if ch == "\\":
            c.i += 1
            if c.eof():
                break
            out.append(c.peek())
            c.i += 1
            continue
        if ch == quote:
            c.i += 1
            return "".join(out)
        out.append(ch)
        c.i += 1
    raise ParseError("Unterminated string literal")


def _parse_expr(c: _Cursor) -> Expr:
    c.consume("{")
    start = c.i
    depth = 1
    while not c.eof() and depth > 0:
        ch = c.peek()
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                expr = c.s[start : c.i].strip()
                c.i += 1
                return Expr(expr)
        c.i += 1
    raise ParseError("Unterminated {expr}")


def _parse_attr_value(c: _Cursor) -> Any:
    c.skip_ws()
    if c.peek() in ("'", '"'):
        return _parse_quoted(c)
    if c.peek() == "{":
        return _parse_expr(c)
    # Numeric literals: <div count=1 /> or <div ratio=1.5 />
    if c.peek().isdigit():
        start = c.i
        while not c.eof() and (c.peek().isdigit() or c.peek() == "."):
            c.i += 1
        lit = c.s[start : c.i]
        try:
            return float(lit) if "." in lit else int(lit)
        except Exception:
            raise ParseError(f"Invalid number literal {lit!r} at {start}") from None
    # Bare identifiers: allow true/false/null for convenience.
    ident = _parse_ident(c)
    if ident == "true":
        return True
    if ident == "false":
        return False
    if ident == "null":
        return None
    return ident


def _parse_attrs(c: _Cursor) -> dict[str, Any]:
    attrs: dict[str, Any] = {}
    while True:
        c.skip_ws()
        if c.peek() in ("/", ">", ""):
            return attrs
        key = _parse_ident(c)
        c.skip_ws()
        if c.peek() == "=":
            c.i += 1
            val = _parse_attr_value(c)
        else:
            # boolean shorthand: <div disabled />
            val = True
        attrs[key] = val


def _parse_element(c: _Cursor) -> Element:
    c.consume("<")
    c.skip_ws()
    tag = _parse_ident(c)
    attrs = _parse_attrs(c)
    c.skip_ws()
    if c.s.startswith("/>", c.i):
        c.i += 2
        return Element(tag=tag, attrs=attrs, children=[])
    c.consume(">")

    children: list[Any] = []
    while True:
        if c.eof():
            raise ParseError(f"Unterminated element <{tag}>")
        if c.s.startswith(f"</{tag}", c.i):
            break
        if c.peek() == "<":
            children.append(_parse_element(c))
            continue
        if c.peek() == "{":
            children.append(_parse_expr(c))
            continue
        children.append(_parse_text_until(c, stop_chars={"<", "{"}))

    c.consume(f"</{tag}")
    c.skip_ws()
    c.consume(">")
    return Element(tag=tag, attrs=attrs, children=children)
