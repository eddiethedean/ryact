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
                from .error_reporting import _is_legacy_container, report_uncaught_error
                from .root import _dom_handle_lifecycle_error, _dom_report_or_reraise_uncaught

                if _dom_handle_lifecycle_error(
                    container,
                    component,
                    err,
                    prefer_first_captured_error=True,
                ):
                    return
                if _is_legacy_container(container):
                    _dom_report_or_reraise_uncaught(container, err)
                    return
                report_uncaught_error(container, err)
                raise err
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


def _run_class_unmount_if_needed(component: Any, *, container: Any = None) -> None:
    component._ryact_mounted = False  # type: ignore[attr-defined]
    if not getattr(component, "_ryact_did_mount", False):
        return
    component._ryact_did_mount = False  # type: ignore[attr-defined]
    cb = getattr(component, "componentWillUnmount", None)
    if callable(cb):
        component._ryact_in_component_will_unmount = True  # type: ignore[attr-defined]
        try:
            cb()
        except BaseException as err:
            dom_container = container or getattr(component, "_ryact_dom_container", None)
            if dom_container is not None:
                from .root import _dom_handle_lifecycle_error, _dom_report_or_reraise_uncaught

                if _dom_handle_lifecycle_error(dom_container, component, err, prefer_first_captured_error=False):
                    return
                _dom_report_or_reraise_uncaught(dom_container, err)
                return
            raise
        finally:
            component._ryact_in_component_will_unmount = False  # type: ignore[attr-defined]


def _should_update_component_host_link(
    old_host: ElementNode,
    new_host: ElementNode,
    *,
    replace: bool,
) -> bool:
    if replace or old_host is new_host:
        return True
    if old_host.parent is None:
        return True
    if _node_in_subtree(old_host, new_host):
        return True
    if _node_in_subtree(new_host, old_host):
        return False
    return False


def _apply_component_host_link(component: Any, host: ElementNode, *, replace: bool = False) -> None:
    comp_id = id(component)
    prev = _component_dom_nodes.get(comp_id)
    if prev is not None:
        old_host = prev[1]
        if not _should_update_component_host_link(old_host, host, replace=replace):
            return
        if old_host is not host and getattr(old_host, "_ryact_component_owner", None) == comp_id:
            old_host._ryact_component_owner = None  # type: ignore[attr-defined]
    _component_dom_nodes[comp_id] = (component, host)
    host._ryact_component_owner = comp_id  # type: ignore[attr-defined]


def link_component_dom_host(
    component: Any,
    host: ElementNode,
    *,
    replace: bool = False,
    container: Any = None,
) -> None:
    """Associate a class instance with its host node without running lifecycles."""

    _apply_component_host_link(component, host, replace=replace)
    if container is None:
        return
    stack = getattr(container, "_ryact_commit_class_stack", None)
    if not isinstance(stack, list):
        return
    try:
        idx = stack.index(component)
    except ValueError:
        return
    for ancestor in stack[:idx]:
        _apply_component_host_link(ancestor, host, replace=False)


def register_component_dom_node(component: Any, host: ElementNode) -> None:
    link_component_dom_host(component, host)
    _run_class_mount_if_needed(component)


def clear_component_dom_node(component: Any, *, container: Any = None) -> None:
    entry = _component_dom_nodes.get(id(component))
    if entry is None:
        return
    component._ryact_find_dom_unmounted = True  # type: ignore[attr-defined]
    dom_container = container or getattr(entry[0], "_ryact_dom_container", None)
    _run_class_unmount_if_needed(entry[0], container=dom_container)
    _component_dom_nodes.pop(id(component), None)


def purge_all_component_dom_registry_for_root(class_instances: dict[Any, Any]) -> None:
    """Drop all component DOM registry entries for instances owned by a root."""

    for inst in list(class_instances.values()):
        clear_component_dom_node(inst)


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


def _is_dom_error_boundary(inst: Any) -> bool:
    return callable(getattr(inst, "componentDidCatch", None)) or callable(
        getattr(type(inst), "getDerivedStateFromError", None)
    )


def purge_class_instances_for_detached_subtree(dom_root: Any, host: ElementNode) -> None:
    """Drop cached class instances whose host nodes were removed from the tree."""

    container = getattr(dom_root, "container", None)
    to_remove: list[tuple[tuple[Any, str | None], Any]] = []
    for key, inst in list(dom_root._class_instances.items()):
        entry = _component_dom_nodes.get(id(inst))
        if entry is None:
            continue
        node = entry[1]
        if node is host or (isinstance(node, ElementNode) and _node_in_subtree(host, node)):
            to_remove.append((key, inst))
    for key, inst in to_remove:
        if _is_dom_error_boundary(inst):
            # Fragment-returning boundaries may be linked to a child host; unlink only.
            _component_dom_nodes.pop(id(inst), None)
            continue
        dom_container = container or getattr(inst, "_ryact_dom_container", None)
        clear_component_dom_node(dom_root._class_instances.pop(key), container=dom_container)


def _warn_find_dom_node_strict_mode_dev(component: Any) -> None:
    from ryact.dev import is_dev

    if not is_dev():
        return
    import warnings

    from ryact.component import Component

    cls_name = type(component).__name__ if isinstance(component, Component) else "Component"
    in_strict = int(getattr(component, "_ryact_dom_strict_depth", 0) or 0) > 0
    renders_strict = bool(getattr(component, "_ryact_dom_renders_strict_child", False))
    if not in_strict and not renders_strict:
        return
    if renders_strict and not in_strict:
        msg = (
            "findDOMNode is deprecated in StrictMode. "
            f"findDOMNode was passed an instance of {cls_name} which renders StrictMode children. "
            "Instead, add a ref directly to the element you want to reference. "
            "Learn more about using refs safely here: "
            "https://react.dev/link/strict-mode-find-node"
        )
    else:
        msg = (
            "findDOMNode is deprecated in StrictMode. "
            f"findDOMNode was passed an instance of {cls_name} which is inside StrictMode. "
            "Instead, add a ref directly to the element you want to reference. "
            "Learn more about using refs safely here: "
            "https://react.dev/link/strict-mode-find-node"
        )
    warnings.warn(msg, RuntimeWarning, stacklevel=3)


def find_dom_node(component_or_host: Any) -> ElementNode | TextNode | None:
    """Minimal ``findDOMNode`` for class instances and host nodes."""

    if component_or_host is None:
        return None
    if isinstance(component_or_host, (ElementNode, TextNode)):
        return component_or_host
    if callable(getattr(component_or_host, "render", None)):
        _warn_find_dom_node_strict_mode_dev(component_or_host)
        entry = _component_dom_nodes.get(id(component_or_host))
        if entry is None:
            if getattr(component_or_host, "_ryact_find_dom_unmounted", False):
                raise RuntimeError("Unable to find node on an unmounted component.")
            return None
        return _first_rendered_host(entry[1])
    if isinstance(component_or_host, dict):
        keys = ", ".join(sorted(str(k) for k in component_or_host))
        raise TypeError(f"Argument appears to not be a ReactComponent. Keys: {keys}")
    raise TypeError("Argument appears to not be a ReactComponent.")


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
            dom_container = getattr(entry[0], "_ryact_dom_container", None)
            _run_class_unmount_if_needed(entry[0], container=dom_container)
        _component_dom_nodes.pop(comp_id, None)
