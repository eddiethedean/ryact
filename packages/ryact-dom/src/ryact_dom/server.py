from __future__ import annotations

from typing import Any

from ryact.element import Element
from ryact.hooks import _render_component

from .html_props import (
    dom_event_type_for_listener_key,
    html_attribute_name,
    normalize_host_prop_dict,
)


def render_to_string(element: Any) -> str:
    """
    Very early server-rendering placeholder.

    The long-term parity target is `react-dom/server` semantics, but this provides
    a deterministic baseline for upcoming translated tests.
    """

    parts = []  # type: List[str]
    _render(element, parts)
    return "".join(parts)


_hooks_by_component = {}  # type: dict[int, list[Any]]


def _get_component_hooks(component: Any) -> list[Any]:
    cid = id(component)
    if cid not in _hooks_by_component:
        _hooks_by_component[cid] = []
    return _hooks_by_component[cid]


def _render(node: Any, out: list[str]) -> None:
    if node is None:
        return
    if isinstance(node, (str, int, float)):
        out.append(str(node))
        return
    if isinstance(node, Element) and isinstance(node.type, str):
        out.append("<" + node.type)
        props_norm = normalize_host_prop_dict(node.props)
        for k, v in props_norm.items():
            if k == "children":
                continue
            if callable(v) and dom_event_type_for_listener_key(k) is not None:
                continue
            if k.startswith("on"):
                continue
            out.append(f' {html_attribute_name(k)}="{v}"')
        out.append(">")
        for c in node.props.get("children", ()):
            _render(c, out)
        out.append("</" + node.type + ">")
        return
    if isinstance(node, Element) and callable(node.type):
        rendered = _render_component(node.type, dict(node.props), _get_component_hooks(node.type))
        _render(rendered, out)
        return
    raise TypeError(f"Unsupported node for server rendering: {type(node)!r}")
