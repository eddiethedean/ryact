"""Host event propagation, capture phase, and emulated bubbling (ReactDOMEventListener parity)."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

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

# React maps these props to bubbling focus events.
_PROPAGATION_TYPE_ALIASES: dict[str, str] = {
    "blur": "focusout",
    "focus": "focusin",
}

# Enter/leave are delegated from over/out events (not native bubble).
_SYNTHETIC_ENTER_LEAVE: dict[str, tuple[str, str]] = {
    "mouseover": ("mouseenter", "enter"),
    "mouseout": ("mouseleave", "leave"),
    "pointerover": ("pointerenter", "enter"),
    "pointerout": ("pointerleave", "leave"),
}

_NO_BUBBLE_TYPES: frozenset[str] = frozenset(
    {
        "scroll",
        "scrollend",
        "mouseenter",
        "mouseleave",
        "pointerenter",
        "pointerleave",
    }
)

_MEDIA_TAGS: frozenset[str] = frozenset({"audio", "video"})
_LOADSTART_TAGS: frozenset[str] = _MEDIA_TAGS

_document_listener_log: list[tuple[str, bool]] = []
_document_event_listeners: list[tuple[str, Callable[[Any], None], bool]] = []
_selectionchange_subscribed: bool = False
_event_dispatch_depth: int = 0


def event_dispatch_in_progress() -> bool:
    """True while a host synthetic event is being dispatched (capture/bubble)."""

    return _event_dispatch_depth > 0


def reset_document_listener_test_state() -> None:
    global _selectionchange_subscribed
    _document_listener_log.clear()
    _document_event_listeners.clear()
    _selectionchange_subscribed = False


def add_document_event_listener(
    type_: str,
    listener: Callable[[Any], None],
    *,
    capture: bool = False,
) -> None:
    """Register a document-level listener (ReactDOMComponent event-order parity)."""

    _document_event_listeners.append((type_, listener, capture))


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


def _propagation_event_type(type_: str) -> str:
    return _PROPAGATION_TYPE_ALIASES.get(type_, type_)


def _listener_keys_for_dispatch(type_: str, bubble_type: str) -> tuple[str, ...]:
    keys: list[str] = []
    for k in (bubble_type, type_):
        if k and k not in keys:
            keys.append(k)
    if bubble_type == "focusout" and "blur" not in keys:
        keys.append("blur")
    if bubble_type == "focusin" and "focus" not in keys:
        keys.append("focus")
    return tuple(keys)


def _should_emulate_bubble(type_: str) -> bool:
    if type_ in _NO_EMULATED_BUBBLE:
        return False
    return _propagation_event_type(type_) in _EMULATED_BUBBLE_TYPES


def _should_bubble_to_ancestor(type_: str) -> bool:
    t = _propagation_event_type(type_)
    if t in _NO_BUBBLE_TYPES or t in _NO_EMULATED_BUBBLE:
        return False
    from .html_props import _REGISTERED_DOM_EVENTS

    return t in _REGISTERED_DOM_EVENTS


def _container_for(node: ElementNode) -> Container | None:
    return node._event_container


def _is_container_root(node: ElementNode | None) -> bool:
    return node is not None and node.tag == "root"


def _is_enter_leave_ancestor(ancestor: ElementNode, node: ElementNode | None) -> bool:
    if node is None or _is_container_root(node):
        return False
    if node is ancestor:
        return True
    seen: set[int] = {id(ancestor)}
    cur: ElementNode | None = node
    while cur is not None:
        if _is_container_root(cur):
            return False
        if cur is ancestor:
            return True
        if id(cur) in seen:
            break
        seen.add(id(cur))
        cur = _event_parent(cur)
    return False


def _should_fire_enter_leave(*, node: ElementNode, phase: str, event: Any) -> bool:
    related = getattr(event, "related_target", None) or getattr(event, "relatedTarget", None)
    if related is None:
        return True
    return not _is_enter_leave_ancestor(node, related)


def _fire_synthetic_enter_leave(
    *,
    path: list[ElementNode],
    type_: str,
    event: Any,
    wrap_event_listener: Callable[[Callable[..., None]], Callable[..., None]],
) -> None:
    spec = _SYNTHETIC_ENTER_LEAVE.get(type_)
    if spec is None:
        return
    enter_type, phase = spec
    ordered = [*reversed(path[1:]), path[0]] if phase == "enter" else path
    for node in ordered:
        if not _should_fire_enter_leave(node=node, phase=phase, event=event):
            continue
        event.current_target = node
        for listener in list(node._listeners.get(enter_type, [])):
            wrap_event_listener(listener)(event)
            if event._stopped:
                return


def _loadstart_allowed(target: ElementNode) -> bool:
    return target.tag.lower() in _LOADSTART_TAGS


def _submit_reset_blocked(target: ElementNode, type_: str) -> bool:
    if type_ not in ("submit", "reset"):
        return False
    node = _event_parent(target)
    while node is not None:
        # Enclosing <form> boundaries are independent; only non-form ancestors block
        # synthetic submit/reset dispatch (see ReactDOMForm nested-form cases).
        if node.tag.lower() != "form" and node._native_blocks_submission:
            return True
        node = _event_parent(node)
    return False


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

        bubble_type = _propagation_event_type(type_)
        listener_keys = _listener_keys_for_dispatch(type_, bubble_type)
        for doc_type, doc_listener, doc_capture in _document_event_listeners:
            if doc_capture and doc_type == type_:
                doc_listener(event)
                if event._stopped:
                    return
        for node in reversed(path):
            event.current_target = node
            for key in listener_keys:
                for listener in list(node._listeners_capture.get(key, [])):
                    wrap_event_listener(listener)(event)
                    if event._stopped:
                        return

        for i, node in enumerate(path):
            if i > 0 and not _should_bubble_to_ancestor(type_):
                break
            if not (skip_listeners and skip_listeners(node)):
                event.current_target = node
                for key in listener_keys:
                    for listener in list(node._listeners.get(key, [])):
                        wrap_event_listener(listener)(event)
                        if event._stopped:
                            return
            nxt = path[i + 1] if i + 1 < len(path) else None
            _maybe_flush_between_roots(node=node, next_node=nxt, type_=type_)

        if not event._stopped:
            _fire_synthetic_enter_leave(
                path=path,
                type_=type_,
                event=event,
                wrap_event_listener=wrap_event_listener,
            )

        if after_listeners is not None:
            after_listeners()
        if not event._stopped:
            for doc_type, doc_listener, doc_capture in _document_event_listeners:
                if not doc_capture and doc_type == type_:
                    doc_listener(event)
    finally:
        _event_dispatch_depth -= 1
        if at_top:
            if continuous:
                _set_batching(containers, False)
            for c in containers:
                _flush_container_updates(c)
