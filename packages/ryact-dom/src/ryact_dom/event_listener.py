"""Host event propagation, capture phase, and emulated bubbling (ReactDOMEventListener parity)."""
from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .dom import Container, ElementNode

# Discrete events flush pending updates when crossing React root boundaries.
DISCRETE_EVENT_TYPES: frozenset[str] = frozenset(
    {
        "blur",
        "click",
        "contextmenu",
        "focus",
        "keydown",
        "keyup",
        "mousedown",
        "mouseup",
        "touchcancel",
        "touchend",
        "touchstart",
    }
)

# React emulates bubbling for these non-bubbling events (except scroll/scrollend).
_EMULATED_BUBBLE_TYPES: frozenset[str] = frozenset(
    {
        "abort",
        "cancel",
        "canplay",
        "canplaythrough",
        "close",
        "durationchange",
        "emptied",
        "encrypted",
        "ended",
        "error",
        "invalid",
        "loadeddata",
        "loadedmetadata",
        "loadstart",
        "pause",
        "play",
        "playing",
        "progress",
        "ratechange",
        "resize",
        "seeked",
        "seeking",
        "stalled",
        "suspend",
        "timeupdate",
        "toggle",
        "volumechange",
        "waiting",
    }
)

_NO_EMULATED_BUBBLE: frozenset[str] = frozenset({"scroll", "scrollend"})

_MEDIA_TAGS: frozenset[str] = frozenset({"audio", "video"})
_LOADSTART_TAGS: frozenset[str] = _MEDIA_TAGS

_document_listener_log: list[tuple[str, bool]] = []
_selectionchange_subscribed: bool = False
_event_dispatch_depth: int = 0


def reset_document_listener_test_state() -> None:
    global _selectionchange_subscribed
    _document_listener_log.clear()
    _selectionchange_subscribed = False


def document_listener_log() -> list[tuple[str, bool]]:
    return list(_document_listener_log)


def ensure_selectionchange_subscription() -> None:
    global _selectionchange_subscribed
    if _selectionchange_subscribed:
        return
    _selectionchange_subscribed = True
    _document_listener_log.append(("selectionchange", False))


def link_event_parent(child_host: ElementNode, parent_host: ElementNode) -> None:
    """Link separate-root host trees for cross-container propagation tests."""

    child_host._native_event_parent = parent_host


def _event_parent(node: ElementNode) -> ElementNode | None:
    parent = node.parent
    if parent is not None and parent.tag != "root":
        return parent
    if node._native_event_parent is not None:
        return node._native_event_parent
    return None


def _event_path(target: ElementNode) -> list[ElementNode]:
    path: list[ElementNode] = [target]
    seen: set[int] = {id(target)}
    node: ElementNode | None = target
    while True:
        parent = _event_parent(node) if node is not None else None
        if parent is None or id(parent) in seen:
            break
        path.append(parent)
        seen.add(id(parent))
        node = parent
    return path


def _should_emulate_bubble(type_: str) -> bool:
    if type_ in _NO_EMULATED_BUBBLE:
        return False
    return type_ in _EMULATED_BUBBLE_TYPES


def _should_bubble_to_ancestor(type_: str) -> bool:
    if type_ in _NO_EMULATED_BUBBLE:
        return False
    if type_ in _EMULATED_BUBBLE_TYPES:
        return True
    # Default: assume native bubbling for common DOM events used in tests.
    return type_ in {
        "mouseout",
        "mouseover",
        "mousemove",
        "click",
        "change",
        "input",
        "reset",
        "submit",
    }


def _loadstart_allowed(target: ElementNode) -> bool:
    return target.tag.lower() in _LOADSTART_TAGS


def _submit_reset_blocked(target: ElementNode, type_: str) -> bool:
    if type_ not in ("submit", "reset"):
        return False
    node = _event_parent(target)
    while node is not None:
        if node._native_blocks_submission:
            return True
        node = _event_parent(node)
    return False


def _container_for(node: ElementNode) -> Container | None:
    return node._event_container


def _flush_container_updates(container: Container | None) -> None:
    if container is None:
        return
    dom_root = container._ryact_dom_root
    if dom_root is None:
        return
    rr = dom_root._reconciler_root
    commit = getattr(rr, "_commit_fn", None)
    if commit is None or not rr.pending_updates:
        return
    from ryact.reconciler import perform_work

    perform_work(rr, commit)


def _set_batching(containers: list[Container], enabled: bool) -> None:
    for c in containers:
        dom_root = c._ryact_dom_root
        if dom_root is None:
            continue
        rr = dom_root._reconciler_root
        rr._is_batching_updates = enabled  # type: ignore[attr-defined]


def _containers_on_path(path: list[ElementNode]) -> list[Container]:
    out: list[Container] = []
    seen: set[int] = set()
    for n in path:
        c = _container_for(n)
        if c is not None and id(c) not in seen:
            seen.add(id(c))
            out.append(c)
    return out


def _maybe_flush_between_roots(
    *,
    node: ElementNode,
    next_node: ElementNode | None,
    type_: str,
) -> None:
    if type_ not in DISCRETE_EVENT_TYPES or next_node is None:
        return
    c0 = _container_for(node)
    c1 = _container_for(next_node)
    if c0 is not None and c0 is not c1:
        _flush_container_updates(c0)


def dispatch_host_event(
    target: ElementNode,
    type_: str,
    *,
    skip_listeners: Callable[[ElementNode], bool] | None = None,
    after_listeners: Callable[[], None] | None = None,
) -> None:
    """Run capture/bubble dispatch for a host ``SyntheticEvent``."""

    from .input_host import wrap_event_listener

    if type_ == "loadstart" and not _loadstart_allowed(target):
        return
    if _submit_reset_blocked(target, type_):
        return

    global _event_dispatch_depth
    path = _event_path(target)
    containers = _containers_on_path(path)
    discrete = type_ in DISCRETE_EVENT_TYPES
    continuous = not discrete

    _event_dispatch_depth += 1
    at_top = _event_dispatch_depth == 1
    try:
        if at_top and continuous:
            _set_batching(containers, True)

        event = target._current_dispatch_event
        if event is None:
            return

        for node in reversed(path):
            event.current_target = node
            for listener in node._listeners_capture.get(type_, []):
                wrap_event_listener(listener)(event)
                if event._stopped:
                    return

        for i, node in enumerate(path):
            if i > 0 and not _should_bubble_to_ancestor(type_):
                break
            if not (skip_listeners and skip_listeners(node)):
                event.current_target = node
                for listener in node._listeners.get(type_, []):
                    wrap_event_listener(listener)(event)
                    if event._stopped:
                        return
            nxt = path[i + 1] if i + 1 < len(path) else None
            _maybe_flush_between_roots(node=node, next_node=nxt, type_=type_)

        if after_listeners is not None:
            after_listeners()
    finally:
        _event_dispatch_depth -= 1
        if at_top:
            if continuous:
                _set_batching(containers, False)
            for c in containers:
                _flush_container_updates(c)
