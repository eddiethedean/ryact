"""Legacy ``ReactDOM.render`` / ``unmountComponentAtNode`` parity (test harness subset)."""
from __future__ import annotations

import warnings
from collections.abc import Callable
from typing import Any

from ryact.dev import is_dev
from ryact.element import Element

from .dom import Container, ElementNode, Node, TextNode
from ryact.reconciler import create_root as create_reconciler_root

from .use_id_host import make_use_id_allocator

if False:  # TYPE_CHECKING
    from .root import Root

_LEGACY_ROOT_BY_CONTAINER: dict[int, Any] = {}
_CONTAINER_MOUNT_MODE: dict[int, str] = {}  # "legacy" | "modern"
_RYACT_OWNER_ID = 1


def _next_owner_id() -> int:
    global _RYACT_OWNER_ID
    _RYACT_OWNER_ID += 1
    return _RYACT_OWNER_ID


def reset_legacy_mount_state() -> None:
    _LEGACY_ROOT_BY_CONTAINER.clear()
    _CONTAINER_MOUNT_MODE.clear()


def container_has_react_render(container: Container) -> bool:
    cid = id(container)
    if cid in _LEGACY_ROOT_BY_CONTAINER:
        return True
    return bool(container.root.children)


def _first_host_node(container: Container) -> ElementNode | None:
    for ch in container.root.children:
        if isinstance(ch, ElementNode):
            return ch
    return None


def _invoke_legacy_callback(root: Any) -> None:
    cb = getattr(root, "_legacy_render_callback", None)
    if not callable(cb):
        return
    host = _first_host_node(root.container)
    if host is None:
        cb()
        return
    host_this = type(
        "LegacyCallbackHost",
        (),
        {"nodeName": host.tagName.upper()},
    )()
    try:
        cb.__func__(host_this)  # type: ignore[attr-defined]
    except (AttributeError, TypeError):
        try:
            cb(host_this)
        except TypeError:
            cb()


def _warn_dev(msg: str) -> None:
    if is_dev():
        warnings.warn(msg, UserWarning, stacklevel=4)


def warn_legacy_render_on_modern_container() -> None:
    _warn_dev(
        "You are calling ReactDOM.render() on a container that was previously "
        "passed to ReactDOMClient.createRoot(). This is not supported. "
        "Did you mean to call root.render(element)?"
    )


def warn_modern_create_root_on_legacy_container() -> None:
    _warn_dev(
        "You are calling ReactDOMClient.createRoot() on a container that was previously "
        "passed to ReactDOM.render(). This is not supported."
    )


def warn_legacy_unmount_on_modern_container() -> None:
    _warn_dev(
        "You are calling ReactDOM.unmountComponentAtNode() on a container that was previously "
        "passed to ReactDOMClient.createRoot(). This is not supported. Did you mean to call "
        "root.unmount()?"
    )


def warn_unmount_not_top_level() -> None:
    _warn_dev(
        "unmountComponentAtNode(): The node you're attempting to unmount was rendered by React "
        "and is not a top-level container. Instead, have the parent component update its state "
        "and rerender in order to remove this component."
    )


def warn_unmount_wrong_react_copy() -> None:
    _warn_dev(
        "unmountComponentAtNode(): The node you're attempting to unmount was rendered by "
        "another copy of React."
    )


def warn_replacing_react_children_with_new_root() -> None:
    _warn_dev(
        "Replacing React-rendered children with a new root component. If you intended to update "
        "the children of this node, you should instead have the existing children update their "
        "state and render the new components instead of calling ReactDOM.render."
    )


def warn_mount_document_body() -> None:
    _warn_dev(
        "render(): Rendering elements directly into document.body is discouraged, "
        "since its children are often manipulated by third-party scripts."
    )


def register_modern_root(container: Container, root: Any) -> None:
    cid = id(container)
    prev = _CONTAINER_MOUNT_MODE.get(cid)
    if prev == "legacy" and is_dev():
        warn_modern_create_root_on_legacy_container()
    _CONTAINER_MOUNT_MODE[cid] = "modern"
    _LEGACY_ROOT_BY_CONTAINER.pop(cid, None)


def legacy_render(
    element: Element | None,
    container: Container,
    callback: Callable[[], None] | None = None,
) -> Any:
    if callback is not None and not callable(callback):
        raise TypeError(
            "ReactDOM.render(...): Expected the last optional `callback` argument to be a function."
        )
    if not isinstance(container, Container):
        raise TypeError("Target container is not a DOM element.")

    cid = id(container)
    if _CONTAINER_MOUNT_MODE.get(cid) == "modern":
        warn_legacy_render_on_modern_container()

    if getattr(container, "_is_document_body", False) and is_dev():
        warn_mount_document_body()

    existing = _LEGACY_ROOT_BY_CONTAINER.get(cid)
    if existing is not None and not existing._unmounted:
        root = existing
    else:
        for ch in list(container.root.children):
            from .root import _detach_host_subtree

            _detach_host_subtree(ch)
        container.root.children.clear()
        owner = getattr(container, "_ryact_owner_id", None)
        if owner is None:
            container._ryact_owner_id = _next_owner_id()  # type: ignore[attr-defined]
        from .root import Root

        root = Root(
            container=container,
            _reconciler_root=create_reconciler_root(container),
            _next_use_id=make_use_id_allocator(identifier_prefix=""),
        )
        container._ryact_dom_root = root
        _LEGACY_ROOT_BY_CONTAINER[cid] = root
        _CONTAINER_MOUNT_MODE[cid] = "legacy"

    if callback is not None:
        root._legacy_render_callback = callback  # type: ignore[attr-defined]
    else:
        root._legacy_render_callback = None  # type: ignore[attr-defined]

    root.render(element)
    if isinstance(element, Element):
        from ryact.hooks import _is_class_component

        if _is_class_component(element.type):
            inst = root._class_instances.get((element.type, element.key))
            if inst is not None:
                return inst
    return root


def unmount_component_at_node(container: Any) -> bool:
    if not isinstance(container, Container):
        raise TypeError("Target container is not a DOM element.")

    cid = id(container)
    if not container_has_react_render(container):
        return False

    if _CONTAINER_MOUNT_MODE.get(cid) == "modern":
        warn_legacy_unmount_on_modern_container()
        warn_unmount_not_top_level()
        return False

    root = _LEGACY_ROOT_BY_CONTAINER.get(cid)
    if root is None:
        _warn_dev(
            "unmountComponentAtNode(): The node you're attempting to unmount was rendered by "
            "another copy of React."
        )
        return False

    root.unmount()
    _LEGACY_ROOT_BY_CONTAINER.pop(cid, None)
    _CONTAINER_MOUNT_MODE.pop(cid, None)
    return True


def batched_updates(fn: Callable[[], Any]) -> Any:
    """``ReactDOM.unstable_batchedUpdates`` — batch across all legacy/modern roots in-process."""

    from ryact.reconciler import perform_work

    from .root import Root

    def _collect_roots() -> list[Any]:
        out: list[Any] = []
        seen_ids: set[int] = set()
        for r in list(_LEGACY_ROOT_BY_CONTAINER.values()):
            rid = id(r)
            if rid not in seen_ids and not r._unmounted:
                seen_ids.add(rid)
                out.append(r)
        from .root_dev import _container_active_root

        for r in list(_container_active_root.values()):
            if isinstance(r, Root) and id(r) not in seen_ids and not r._unmounted:
                seen_ids.add(id(r))
                out.append(r)
        return out

    roots = _collect_roots()
    if not roots:
        return fn()

    prev_batch = [
        bool(getattr(r._reconciler_root, "_is_batching_updates", False)) for r in roots
    ]
    try:
        for r in roots:
            r._reconciler_root._is_batching_updates = True  # type: ignore[attr-defined]
        result = fn()
    finally:
        for r, was in zip(roots, prev_batch, strict=True):
            r._reconciler_root._is_batching_updates = was  # type: ignore[attr-defined]

    from ryact.reconciler import SYNC_LANE, Update, schedule_update_on_root

    from ryact.reconciler import _apply_queued_class_state_for_sync_render

    roots = _collect_roots()
    for r in roots:
        rr = r._reconciler_root
        for inst in r._class_instances.values():
            _apply_queued_class_state_for_sync_render(inst, rr, strict=False)
    for r in roots:
        rr = r._reconciler_root
        commit = getattr(rr, "_commit_fn", None)
        if not callable(commit) or not rr.pending_updates:
            continue
        promoted: list[Update] = []
        for u in rr.pending_updates:
            if int(u.lane.priority) > int(SYNC_LANE.priority):
                promoted.append(
                    Update(
                        lane=SYNC_LANE,
                        payload=u.payload,
                        from_passive_effect=bool(getattr(u, "from_passive_effect", False)),
                        batched_with_force=bool(getattr(u, "batched_with_force", False)),
                    )
                )
            else:
                promoted.append(u)
        rr.pending_updates = promoted
        perform_work(rr, commit)
    for r in roots:
        rr = r._reconciler_root
        commit = getattr(rr, "_commit_fn", None)
        if not callable(commit):
            continue
        pending_state = False
        for inst in r._class_instances.values():
            pu = getattr(inst, "_pending_state_updates", None)
            if isinstance(pu, list) and pu:
                pending_state = True
                break
        if pending_state and getattr(rr, "_last_element", None) is not None:
            from ryact.reconciler import Update

            schedule_update_on_root(rr, Update(lane=SYNC_LANE, payload=rr._last_element))
            perform_work(rr, commit)
    return result
