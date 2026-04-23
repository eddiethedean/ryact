from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Optional, Union

from ryact.element import Element
from ryact.hooks import _render_with_hooks
from ryact.reconciler import DEFAULT_LANE, Update, create_root as create_reconciler_root, perform_work, schedule_update_on_root

from .dom import Container, ElementNode, TextNode


Renderable = Union[Element, str, int, float, None]


def _render_element(node: Renderable) -> List[Any]:
    if node is None:
        return []
    if isinstance(node, (str, int, float)):
        return [TextNode(text=str(node))]
    if isinstance(node, Element):
        # Host element is a string tag for now.
        if isinstance(node.type, str):
            el = ElementNode(tag=node.type, props=dict(node.props))
            for prop, value in list(el.props.items()):
                if prop.startswith("on") and callable(value):
                    # Very early event mapping: onClick -> click
                    event_type = prop[2:].lower()
                    el.add_event_listener(event_type, value)
                    del el.props[prop]
            children = node.props.get("children", ())
            for c in children:
                for rendered in _render_element(c):
                    el.append_child(rendered)
            return [el]
        # Function component: call with props.
        if callable(node.type):
            rendered = _render_with_hooks(node.type, dict(node.props), _get_component_hooks(node.type))
            return _render_element(rendered)
    raise TypeError(f"Unsupported node type: {type(node)!r}")


_hooks_by_component = {}  # type: dict[int, list[Any]]


def _get_component_hooks(component: Any) -> List[Any]:
    # Very early identity model: key by function object identity.
    cid = id(component)
    if cid not in _hooks_by_component:
        _hooks_by_component[cid] = []
    return _hooks_by_component[cid]


@dataclass
class Root:
    container: Container
    _reconciler_root: Any

    def render(self, element: Optional[Element]) -> None:
        def commit(payload: Any) -> None:
            self.container.root.children.clear()
            for child in _render_element(payload):
                self.container.root.append_child(child)

        schedule_update_on_root(self._reconciler_root, Update(lane=DEFAULT_LANE, payload=element))
        perform_work(self._reconciler_root, commit)


def create_root(container: Container) -> Root:
    return Root(container=container, _reconciler_root=create_reconciler_root(container))

