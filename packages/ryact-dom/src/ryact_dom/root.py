from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional, Union

from ryact.concurrent import Fragment, Portal
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


def _render_element(node: Renderable, *, portal_targets: list[Any]) -> list[Any]:
    if node is None:
        return []
    if isinstance(node, (str, int, float)):
        return [TextNode(text=str(node))]
    if isinstance(node, Element):
        # Host element is a string tag for now.
        if isinstance(node.type, str):
            if node.type == Fragment:
                out: list[Any] = []
                children = node.props.get("children", ())
                for c in children:
                    out.extend(_render_element(c, portal_targets=portal_targets))
                return out
            if node.type == Portal:
                target = node.props.get("container")
                if target is not None:
                    if target not in portal_targets:
                        portal_targets.append(target)
                    assert hasattr(target, "root")
                    target.root.children.clear()
                    children = node.props.get("children", ())
                    for c in children:
                        for rendered in _render_element(c, portal_targets=portal_targets):
                            target.root.append_child(rendered)
                return []
            el = ElementNode(tag=node.type, props=normalize_host_prop_dict(node.props))
            for prop, value in list(el.props.items()):
                if is_event_listener_prop(prop, value):
                    event_type = dom_event_type_for_listener_key(prop)
                    assert event_type is not None
                    el.add_event_listener(event_type, value)
                    del el.props[prop]
            children = node.props.get("children", ())
            for c in children:
                for rendered in _render_element(c, portal_targets=portal_targets):
                    el.append_child(rendered)
            return [el]
        # Function or class component (see ryact.Component).
        if callable(node.type):
            rendered = _render_component(
                node.type, dict(node.props), _get_component_hooks(node.type)
            )
            return _render_element(rendered, portal_targets=portal_targets)
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
    _portal_targets: list[Any] | None = None
    _hydrating: bool = False
    _on_recoverable_error: Callable[[Exception], None] | None = None

    def render(self, element: Element | None, *, lane: Lane = DEFAULT_LANE) -> None:
        def commit(payload: Any) -> None:
            if self._hydrating:
                # Minimal hydration slice: compare existing host tree with next payload and
                # report a recoverable mismatch, then replace.
                try:
                    _detect_hydration_mismatch(self.container, payload)
                except Exception as err:
                    if self._on_recoverable_error is not None:
                        self._on_recoverable_error(err)
            self.container.root.children.clear()
            if self._portal_targets is None:
                self._portal_targets = []
            for prev in list(self._portal_targets):
                if hasattr(prev, "root"):
                    prev.root.children.clear()
            portal_targets: list[Any] = []
            for child in _render_element(payload, portal_targets=portal_targets):
                self.container.root.append_child(child)
            self._portal_targets = portal_targets

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


def hydrate_root(
    container: Container,
    element: Element | None,
    *,
    scheduler: Optional[Scheduler] = None,
    on_recoverable_error: Callable[[Exception], None] | None = None,
) -> Root:
    root = create_root(container, scheduler=scheduler)
    root._hydrating = True
    root._on_recoverable_error = on_recoverable_error
    root.render(element)
    return root


def _detect_hydration_mismatch(container: Container, payload: Any) -> None:
    # Very small mismatch detector: compare first host child tag + first text.
    existing = container.root.children[0] if container.root.children else None
    rendered = _render_element(payload, portal_targets=[])
    next0 = rendered[0] if rendered else None

    if isinstance(existing, ElementNode) and isinstance(next0, ElementNode):
        if existing.tag != next0.tag:
            raise ValueError(f"Hydration mismatch: tag {existing.tag!r} != {next0.tag!r}")
        # Compare first text child if both have one.
        ex_text = existing.children[0] if existing.children else None
        nx_text = next0.children[0] if next0.children else None
        if (
            isinstance(ex_text, TextNode)
            and isinstance(nx_text, TextNode)
            and ex_text.text != nx_text.text
        ):
            raise ValueError(f"Hydration mismatch: text {ex_text.text!r} != {nx_text.text!r}")
    elif existing is not None or next0 is not None:
        raise ValueError("Hydration mismatch: existing and next trees differ")
