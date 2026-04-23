from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Union

from ryact.element import Element
from ryact.hooks import _render_with_hooks

from .native import NativeContainer, NativeText, NativeView

Renderable = Union[Element, str, int, float, None]

_hooks_by_component = {}  # type: dict[int, list[Any]]


def _get_component_hooks(component: Any) -> list[Any]:
    cid = id(component)
    if cid not in _hooks_by_component:
        _hooks_by_component[cid] = []
    return _hooks_by_component[cid]


def _render(node: Renderable) -> list[Any]:
    if node is None:
        return []
    if isinstance(node, (str, int, float)):
        return [NativeText(text=str(node))]
    if isinstance(node, Element):
        if isinstance(node.type, str):
            view = NativeView(name=node.type, props=dict(node.props))
            for c in node.props.get("children", ()):
                for rendered in _render(c):
                    view.append_child(rendered)
            return [view]
        if callable(node.type):
            rendered = _render_with_hooks(
                node.type, dict(node.props), _get_component_hooks(node.type)
            )
            return _render(rendered)
    raise TypeError(f"Unsupported native render node: {type(node)!r}")


@dataclass
class Root:
    container: NativeContainer

    def render(self, element: Element | None) -> None:
        self.container.root.children.clear()
        for child in _render(element):
            self.container.root.append_child(child)


def create_root(container: NativeContainer) -> Root:
    return Root(container=container)
