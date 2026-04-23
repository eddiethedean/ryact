from __future__ import annotations

from typing import Any

from ryact.element import Element


def render_to_string(element: Any) -> str:
    """
    Very early server-rendering placeholder.

    The long-term parity target is `react-dom/server` semantics, but this provides
    a deterministic baseline for upcoming translated tests.
    """

    parts = []  # type: List[str]
    _render(element, parts)
    return "".join(parts)


def _render(node: Any, out: list[str]) -> None:
    if node is None:
        return
    if isinstance(node, (str, int, float)):
        out.append(str(node))
        return
    if isinstance(node, Element) and isinstance(node.type, str):
        out.append("<" + node.type)
        for k, v in node.props.items():
            if k == "children" or k.startswith("on"):
                continue
            out.append(f' {k}="{v}"')
        out.append(">")
        for c in node.props.get("children", ()):
            _render(c, out)
        out.append("</" + node.type + ">")
        return
    if isinstance(node, Element) and callable(node.type):
        rendered = node.type(**dict(node.props))
        _render(rendered, out)
        return
    raise TypeError(f"Unsupported node for server rendering: {type(node)!r}")
