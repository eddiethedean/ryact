"""Test/dev DOM internals (findDOMNode parity subset)."""
from __future__ import annotations

from typing import Any

from .dom import ElementNode

_component_dom_nodes: dict[int, ElementNode] = {}


def register_component_dom_node(component: Any, host: ElementNode) -> None:
    _component_dom_nodes[id(component)] = host


def clear_component_dom_node(component: Any) -> None:
    _component_dom_nodes.pop(id(component), None)


def find_dom_node(component_or_host: Any) -> ElementNode | None:
    """Minimal ``findDOMNode`` for class instances and host nodes."""

    if isinstance(component_or_host, ElementNode):
        return component_or_host
    return _component_dom_nodes.get(id(component_or_host))


def reset_component_dom_registry() -> None:
    _component_dom_nodes.clear()
