"""Test/dev DOM internals (findDOMNode parity subset)."""
from __future__ import annotations

from typing import Any

from .dom import ElementNode, Node, TextNode

_component_dom_nodes: dict[int, tuple[Any, ElementNode]] = {}


def mark_class_component_committed(component: Any) -> None:
    """DOM virtual-tree render: class instance is live for updates (refs attach pre-commit)."""
    component._ryact_mounted = True  # type: ignore[attr-defined]


def _run_class_mount_if_needed(component: Any, *, container: Any = None) -> None:
    mark_class_component_committed(component)
    if getattr(component, "_ryact_did_mount", False):
        return
    component._ryact_did_mount = True  # type: ignore[attr-defined]
    component._ryact_pending_mount = False  # type: ignore[attr-defined]
    cb = getattr(component, "componentDidMount", None)
    if callable(cb):
        try:
            cb()
        except BaseException as err:
            if container is not None:
                from .root import _dom_handle_lifecycle_error

                if _dom_handle_lifecycle_error(container, component, err):
                    return
            raise


def _flush_class_setstate_callbacks(instance: Any) -> None:
    pending = getattr(instance, "_pending_setstate_callbacks", None)
    if not isinstance(pending, list) or not pending:
        return
    callbacks = list(pending)
    pending.clear()
    for cb in callbacks:
        if callable(cb):
            cb()


def _run_class_unmount_if_needed(component: Any) -> None:
    component._ryact_mounted = False  # type: ignore[attr-defined]
    if not getattr(component, "_ryact_did_mount", False):
        return
    component._ryact_did_mount = False  # type: ignore[attr-defined]
    cb = getattr(component, "componentWillUnmount", None)
    if callable(cb):
        component._ryact_in_component_will_unmount = True  # type: ignore[attr-defined]
        try:
            cb()
        finally:
            component._ryact_in_component_will_unmount = False  # type: ignore[attr-defined]


def link_component_dom_host(component: Any, host: ElementNode) -> None:
    """Associate a class instance with its host node without running lifecycles."""

    comp_id = id(component)
    prev = _component_dom_nodes.get(comp_id)
    if prev is not None:
        old_host = prev[1]
        if old_host is not host and getattr(old_host, "_ryact_component_owner", None) == comp_id:
            old_host._ryact_component_owner = None  # type: ignore[attr-defined]
    _component_dom_nodes[comp_id] = (component, host)
    host._ryact_component_owner = comp_id  # type: ignore[attr-defined]


def register_component_dom_node(component: Any, host: ElementNode) -> None:
    link_component_dom_host(component, host)
    _run_class_mount_if_needed(component)


def clear_component_dom_node(component: Any) -> None:
    entry = _component_dom_nodes.get(id(component))
    if entry is None:
        return
    _run_class_unmount_if_needed(entry[0])
    _component_dom_nodes.pop(id(component), None)


def _first_rendered_host(node: Node) -> ElementNode | TextNode | None:
    if isinstance(node, TextNode):
        return node
    if isinstance(node, ElementNode):
        text_fallback: TextNode | None = None
        for ch in node.children:
            found = _first_rendered_host(ch)
            if isinstance(found, ElementNode):
                return found
            if isinstance(found, TextNode) and text_fallback is None:
                text_fallback = found
        if node.tag != "root":
            return node
        return text_fallback
    return None


def _node_in_subtree(root: ElementNode, target: Node) -> bool:
    if root is target:
        return True
    for ch in root.children:
        if ch is target:
            return True
        if isinstance(ch, ElementNode) and _node_in_subtree(ch, target):
            return True
    return False


def purge_class_instances_for_detached_subtree(dom_root: Any, host: ElementNode) -> None:
    """Drop cached class instances whose host nodes were removed from the tree."""

    to_remove: list[tuple[Any, str | None]] = []
    for key, inst in list(dom_root._class_instances.items()):
        entry = _component_dom_nodes.get(id(inst))
        if entry is None:
            continue
        node = entry[1]
        if node is host or (isinstance(node, ElementNode) and _node_in_subtree(host, node)):
            to_remove.append(key)
    for key in to_remove:
        clear_component_dom_node(dom_root._class_instances.pop(key))


def find_dom_node(component_or_host: Any) -> ElementNode | TextNode | None:
    """Minimal ``findDOMNode`` for class instances and host nodes."""

    if isinstance(component_or_host, (ElementNode, TextNode)):
        return component_or_host
    entry = _component_dom_nodes.get(id(component_or_host))
    if entry is None:
        return None
    return _first_rendered_host(entry[1])


def reset_component_dom_registry() -> None:
    _component_dom_nodes.clear()


def purge_component_dom_registry_for_subtree(host: ElementNode) -> None:
    """Drop registry entries for hosts removed from the tree (DOM instance cache purge)."""

    ids_to_remove: list[int] = []

    def walk(n: ElementNode) -> None:
        for comp_id, (_inst, node) in list(_component_dom_nodes.items()):
            if node is n:
                ids_to_remove.append(comp_id)
        for ch in n.children:
            if isinstance(ch, ElementNode):
                walk(ch)

    walk(host)
    for comp_id in ids_to_remove:
        entry = _component_dom_nodes.get(comp_id)
        if entry is not None:
            _run_class_unmount_if_needed(entry[0])
        _component_dom_nodes.pop(comp_id, None)
