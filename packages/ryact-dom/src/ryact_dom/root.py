from __future__ import annotations

import warnings
from dataclasses import dataclass, replace
from typing import Any, Callable, Optional, Union, cast

from ryact.concurrent import Fragment, Portal
from ryact.dev import is_dev
from ryact.element import Element, create_element
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
from ryact.wrappers import ForwardRefType, MemoType
from schedulyr import Scheduler

from .dom import Container, ElementNode, Node, TextNode
from .html_props import (
    dom_event_type_for_listener_key,
    is_event_listener_prop,
    normalize_host_prop_dict,
)

Renderable = Union[Element, str, int, float, None]

_dom_component_stack: list[str] = []


class _StackFrame:
    def __init__(self, name: str) -> None:
        self._name = name

    def __enter__(self) -> None:
        _dom_component_stack.append(self._name)

    def __exit__(self, exc_type, exc, tb) -> bool | None:
        if _dom_component_stack and _dom_component_stack[-1] == self._name:
            _dom_component_stack.pop()
        return None


def _dom_stack_str() -> str:
    from ryact.devtools import format_component_stack

    # React-ish: innermost last; we record push on call so stack is outer->inner.
    return format_component_stack(list(_dom_component_stack))


def _op(container: Container, payload: dict[str, object]) -> None:
    container.ops.append(payload)


@dataclass(frozen=True)
class RenderedText:
    text: str


@dataclass(frozen=True)
class RenderedElement:
    tag: str
    key: str | None
    props: dict[str, Any]
    listeners: dict[str, list[Callable[[Any], None]]]
    owner_stack: str
    children: list[RenderedNode]


RenderedNode = RenderedText | RenderedElement


def _render_to_virtual(
    node: Renderable, *, portal_targets: list[Any], container: Container | None = None
) -> list[RenderedNode]:
    if node is None:
        return []
    if isinstance(node, (str, int, float)):
        return [RenderedText(text=str(node))]
    if not isinstance(node, Element):
        raise TypeError(f"Unsupported node type: {type(node)!r}")

    # Host element
    if isinstance(node.type, str):
        if node.type in ("__js_subtree__", "__py_subtree__"):
            if container is None or container.interop_runner is None:
                raise RuntimeError(
                    "Interop boundary encountered but no interop_runner is configured on the "
                    "DOM container."
                )
            runner = container.interop_runner
            boundary_id = "dom"  # deterministic, host-owned (can be refined later)
            props = node.props.get("props") if isinstance(node.props, dict) else None
            children = node.props.get("children", ()) if isinstance(node.props, dict) else ()
            if node.type == "__js_subtree__":
                module_id = str(node.props.get("module_id"))
                export = str(node.props.get("export", "default"))
                rendered = runner.render_js(
                    module_id=module_id,
                    export=export,
                    props=cast(dict[str, object] | None, props),
                    children=cast(tuple[object, ...], children),
                    boundary_id=boundary_id,
                )
            else:
                component_id = str(node.props.get("component_id"))
                rendered = runner.render_py(
                    component_id=component_id,
                    props=cast(dict[str, object] | None, props),
                    children=cast(tuple[object, ...], children),
                    boundary_id=boundary_id,
                )
            return _render_to_virtual(
                cast(Renderable, rendered),
                portal_targets=portal_targets,
                container=container,
            )
        if node.type == Fragment:
            out: list[RenderedNode] = []
            children = node.props.get("children", ())
            for c in children:
                out.extend(
                    _render_to_virtual(c, portal_targets=portal_targets, container=container)
                )
            return out
        if node.type == Portal:
            # Keep portal behavior as a side-effected subtree for now (non-goal for
            # incremental contract).
            target = node.props.get("container")
            if target is not None:
                if target not in portal_targets:
                    portal_targets.append(target)
                assert hasattr(target, "root")
                # Rebuild portal target for now (Phase 24 is about primary root incremental
                # commits).
                target.root.children.clear()
                children = node.props.get("children", ())
                for c in children:
                    for rendered in _render_element(c, portal_targets=portal_targets):
                        target.root.append_child(rendered)
            return []

        props = normalize_host_prop_dict(node.props, tag=node.type)
        listeners: dict[str, list[Callable[[Any], None]]] = {}
        for prop, value in list(props.items()):
            if is_event_listener_prop(prop, value):
                event_type = dom_event_type_for_listener_key(prop)
                assert event_type is not None
                listeners.setdefault(event_type, []).append(cast(Callable[[Any], None], value))
                del props[prop]

        children = node.props.get("children", ())
        rendered_children: list[RenderedNode] = []
        for c in children:
            rendered_children.extend(
                _render_to_virtual(c, portal_targets=portal_targets, container=container)
            )
        return [
            RenderedElement(
                tag=node.type,
                key=node.key,
                props=props,
                listeners=listeners,
                owner_stack=_dom_stack_str(),
                children=rendered_children,
            )
        ]

    # Wrapper/component types
    if isinstance(node.type, MemoType):
        return _render_to_virtual(
            create_element(node.type.inner, dict(node.props), ref=node.ref),
            portal_targets=portal_targets,
            container=container,
        )
    if isinstance(node.type, ForwardRefType):
        rendered = node.type.render(dict(node.props), node.ref)
        return _render_to_virtual(rendered, portal_targets=portal_targets, container=container)
    if callable(node.type):
        name = getattr(node.type, "__name__", "Anonymous")
        with _StackFrame(name):
            rendered = _render_component(
                node.type, dict(node.props), _get_component_hooks(node.type)
            )
            return _render_to_virtual(rendered, portal_targets=portal_targets, container=container)

    raise TypeError(f"Unsupported element type: {node.type!r}")


def _commit_children(
    *,
    container: Container,
    parent: ElementNode,
    next_children: list[RenderedNode],
    path: list[int],
    owner_stack: str = "",
) -> None:
    prev_children = list(parent.children)

    def make_node(v: RenderedNode) -> Node:
        if isinstance(v, RenderedText):
            return TextNode(text=v.text)
        el = ElementNode(tag=v.tag, key=v.key, props=dict(v.props))
        el._listeners = {k: list(vs) for k, vs in v.listeners.items()}
        return el

    def can_reuse(prev: Node, nxt: RenderedNode) -> bool:
        if isinstance(prev, TextNode) and isinstance(nxt, RenderedText):
            return True
        if isinstance(prev, ElementNode) and isinstance(nxt, RenderedElement):
            return prev.tag == nxt.tag and prev.key == nxt.key
        return False

    def apply_updates(node: Node, nxt: RenderedNode, p: list[int]) -> None:
        if isinstance(node, TextNode) and isinstance(nxt, RenderedText):
            if node.text != nxt.text:
                node.text = nxt.text
                _op(container, {"op": "text", "path": list(p), "value": nxt.text})
            return
        if isinstance(node, ElementNode) and isinstance(nxt, RenderedElement):
            if (
                nxt.tag.lower() == "input"
                and "value" in node.props
                and "value" not in nxt.props
            ):
                # Upstream: DOMPropertyOperations "should not remove attributes for special
                # properties" — when an input was controlled, clearing `value` does not clear the
                # value attribute; React also warns in DEV in this situation.
                if is_dev():
                    warnings.warn(
                        "A component is changing a controlled input to be uncontrolled. "
                        "This is likely caused by the value changing from a defined to "
                        "undefined, which should not happen. Decide between using a controlled "
                        "or uncontrolled input element for the lifetime of the component. "
                        "More info: https://react.dev/link/controlled-components\n"
                        "    in input",
                        UserWarning,
                        stacklevel=2,
                    )
                nxt = replace(nxt, props={**nxt.props, "value": node.props["value"]})
            # props diff
            changed: dict[str, Any] = {}
            removed: list[str] = []
            for k, v in nxt.props.items():
                if node.props.get(k) != v:
                    changed[k] = v
            for k in list(node.props.keys()):
                if k not in nxt.props:
                    removed.append(k)
            if changed or removed:
                for k in removed:
                    del node.props[k]
                node.props.update(changed)
                _op(
                    container,
                    {
                        "op": "updateProps",
                        "path": list(p),
                        "props": {**changed, **{k: None for k in removed}},
                    },
                )
            node._listeners = {k: list(vs) for k, vs in nxt.listeners.items()}
            _commit_children(
                container=container,
                parent=node,
                next_children=nxt.children,
                path=list(p) + [0],
                owner_stack=nxt.owner_stack,
            )
            return
        raise TypeError("commit apply_updates: incompatible node types")

    # Determine keyed reconciliation.
    keyed = any(isinstance(c, RenderedElement) and c.key is not None for c in next_children)
    if keyed:
        # Warn for duplicated keys (React-ish), including component stack info when available.
        seen: set[str] = set()
        dups: set[str] = set()
        for c in next_children:
            if isinstance(c, RenderedElement) and c.key is not None:
                if c.key in seen:
                    dups.add(c.key)
                else:
                    seen.add(c.key)
        if dups:
            from ryact_testkit.warnings import emit_warning

            keys = ", ".join(sorted(dups))
            msg = f"Encountered two children with the same key: {keys}"
            if owner_stack:
                msg = msg + "\n\n" + owner_stack
            emit_warning(msg, category=RuntimeWarning, stacklevel=3)

        prev_by_key: dict[str, Node] = {}
        prev_indices: dict[str, int] = {}
        for i, c2 in enumerate(prev_children):
            if isinstance(c2, ElementNode):
                k = c2.key
                if k is not None and k not in prev_by_key:
                    prev_by_key[k] = c2
                    prev_indices[k] = i

        next_nodes: list[Node] = []
        for new_i, v in enumerate(next_children):
            if isinstance(v, RenderedElement) and v.key is not None and v.key in prev_by_key:
                n = prev_by_key[v.key]
                next_nodes.append(n)
            else:
                n = make_node(v)
                next_nodes.append(n)
                _op(
                    container,
                    {
                        "op": "insert",
                        "path": list(path) + [new_i],
                        "tag": getattr(n, "tag", "#text"),
                        "key": getattr(v, "key", None) if isinstance(v, RenderedElement) else None,
                    },
                )

        # Deletes: anything prev keyed not present in next keys.
        next_keys = {
            v.key for v in next_children if isinstance(v, RenderedElement) and v.key is not None
        }
        for old_i, c3 in enumerate(prev_children):
            if isinstance(c3, ElementNode):
                k = c3.key
                if k is not None and k not in next_keys:
                    _op(container, {"op": "delete", "path": list(path) + [old_i], "key": k})

        # Moves: compare prev index to new index for reused keyed nodes.
        for new_i, v in enumerate(next_children):
            if isinstance(v, RenderedElement) and v.key is not None and v.key in prev_indices:
                old_i = prev_indices[v.key]
                if old_i != new_i:
                    _op(
                        container,
                        {
                            "op": "move",
                            "path": list(path),
                            "from": old_i,
                            "to": new_i,
                            "key": v.key,
                        },
                    )

        parent.children = next_nodes
        for i, (n, v) in enumerate(zip(parent.children, next_children, strict=True)):
            n.parent = parent
            apply_updates(n, v, list(path) + [i])
        return

    # Unkeyed: minimal index-based reconciliation.
    next_nodes2: list[Node] = []
    min_len = min(len(prev_children), len(next_children))
    for i in range(min_len):
        prev = prev_children[i]
        nxt = next_children[i]
        if can_reuse(prev, nxt):
            next_nodes2.append(prev)
        else:
            n = make_node(nxt)
            next_nodes2.append(n)
            _op(
                container,
                {
                    "op": "insert",
                    "path": list(path) + [i],
                    "tag": getattr(n, "tag", "#text"),
                    "key": None,
                },
            )

    # Inserts
    for i in range(min_len, len(next_children)):
        nxt = next_children[i]
        n = make_node(nxt)
        next_nodes2.append(n)
        _op(
            container,
            {
                "op": "insert",
                "path": list(path) + [i],
                "tag": getattr(n, "tag", "#text"),
                "key": None,
            },
        )

    # Deletes
    for i in range(len(next_children), len(prev_children)):
        _op(container, {"op": "delete", "path": list(path) + [i]})

    parent.children = next_nodes2
    for i, (n, v) in enumerate(zip(parent.children, next_children, strict=True)):
        n.parent = parent
        apply_updates(n, v, list(path) + [i])


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
            el = ElementNode(
                tag=node.type,
                key=node.key,
                props=normalize_host_prop_dict(node.props, tag=node.type),
            )
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
        if isinstance(node.type, MemoType):
            # DOM renderer is currently clear+rebuild; treat memo as a transparent wrapper.
            return _render_element(
                create_element(node.type.inner, dict(node.props), ref=node.ref),
                portal_targets=portal_targets,
            )
        if isinstance(node.type, ForwardRefType):
            rendered = node.type.render(dict(node.props), node.ref)
            return _render_element(rendered, portal_targets=portal_targets)
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
            # Phase 24: incremental commit into existing host tree.
            self.container.ops.clear()
            if self._portal_targets is None:
                self._portal_targets = []
            for prev in list(self._portal_targets):
                if hasattr(prev, "root"):
                    prev.root.children.clear()
            portal_targets: list[Any] = []
            next_v = _render_to_virtual(
                payload, portal_targets=portal_targets, container=self.container
            )
            _commit_children(
                container=self.container,
                parent=self.container.root,
                next_children=next_v,
                path=[],
                owner_stack="",
            )
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
