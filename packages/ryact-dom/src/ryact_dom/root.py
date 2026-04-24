from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Union

from ryact.element import Element
from ryact.hooks import _render_component
from ryact.reconciler import (
    DEFAULT_LANE,
    Lane,
    Update,
    bind_commit,
    perform_work,
    schedule_update_on_root,
)
from ryact.reconciler import (
    create_root as create_reconciler_root,
)
from schedulyr import Scheduler

from .dom import Container, ElementNode, TextNode
from .html_props import (
    dom_event_type_for_listener_key,
    is_event_listener_prop,
    normalize_host_prop_dict,
)

Renderable = Union[Element, str, int, float, None]


def _render_element(node: Renderable) -> list[Any]:
    if node is None:
        return []
    if isinstance(node, (str, int, float)):
        return [TextNode(text=str(node))]
    if isinstance(node, Element):
        # Host element is a string tag for now.
        if isinstance(node.type, str):
            el = ElementNode(tag=node.type, props=normalize_host_prop_dict(node.props))
            for prop, value in list(el.props.items()):
                if is_event_listener_prop(prop, value):
                    event_type = dom_event_type_for_listener_key(prop)
                    assert event_type is not None
                    el.add_event_listener(event_type, value)
                    del el.props[prop]
            children = node.props.get("children", ())
            for c in children:
                for rendered in _render_element(c):
                    el.append_child(rendered)
            return [el]
        # Function or class component (see ryact.Component).
        if callable(node.type):
            rendered = _render_component(
                node.type, dict(node.props), _get_component_hooks(node.type)
            )
            return _render_element(rendered)
    raise TypeError(f"Unsupported node type: {type(node)!r}")


_hooks_by_component = {}  # type: dict[int, list[Any]]


def _get_component_hooks(component: Any) -> list[Any]:
    # Very early identity model: key by function object identity.
    cid = id(component)
    if cid not in _hooks_by_component:
        _hooks_by_component[cid] = []
    return _hooks_by_component[cid]


@dataclass
class Root:
    container: Container
    _reconciler_root: Any

    def render(self, element: Element | None, *, lane: Lane = DEFAULT_LANE) -> None:
        def commit(payload: Any) -> None:
            self.container.root.children.clear()
            for child in _render_element(payload):
                self.container.root.append_child(child)

        rr = self._reconciler_root
        bind_commit(rr, commit)
        schedule_update_on_root(rr, Update(lane=lane, payload=element))
        if rr.scheduler is None:
            perform_work(rr, commit)


def create_root(container: Container, scheduler: Optional[Scheduler] = None) -> Root:
    return Root(
        container=container,
        _reconciler_root=create_reconciler_root(container, scheduler=scheduler),
    )
