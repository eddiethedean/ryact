"""Test/dev DOM internals (findDOMNode parity subset)."""
from __future__ import annotations

from typing import Any

from .dom import ElementNode

_component_dom_nodes: dict[int, tuple[Any, ElementNode]] = {}


def mark_class_component_committed(component: Any) -> None:
    """DOM virtual-tree render: class instance is live for updates (refs attach pre-commit)."""
    component._ryact_mounted = True  # type: ignore[attr-defined]


def _run_class_mount_if_needed(component: Any) -> None:
    mark_class_component_committed(component)
    if getattr(component, "_ryact_did_mount", False):
        return
    component._ryact_did_mount = True  # type: ignore[attr-defined]
    cb = getattr(component, "componentDidMount", None)
    if callable(cb):
        cb()


def _run_class_unmount_if_needed(component: Any) -> None:
    component._ryact_mounted = False  # type: ignore[attr-defined]
    if not getattr(component, "_ryact_did_mount", False):
        return
    component._ryact_did_mount = False  # type: ignore[attr-defined]
    cb = getattr(component, "componentWillUnmount", None)
    if callable(cb):
        cb()


def register_component_dom_node(component: Any, host: ElementNode) -> None:
    _component_dom_nodes[id(component)] = (component, host)
    _run_class_mount_if_needed(component)


def clear_component_dom_node(component: Any) -> None:
    entry = _component_dom_nodes.pop(id(component), None)
    if entry is not None:
        _run_class_unmount_if_needed(entry[0])


def find_dom_node(component_or_host: Any) -> ElementNode | None:
    """Minimal ``findDOMNode`` for class instances and host nodes."""

    if isinstance(component_or_host, ElementNode):
        return component_or_host
    entry = _component_dom_nodes.get(id(component_or_host))
    return entry[1] if entry is not None else None


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
        entry = _component_dom_nodes.pop(comp_id, None)
        if entry is not None:
            _run_class_unmount_if_needed(entry[0])
