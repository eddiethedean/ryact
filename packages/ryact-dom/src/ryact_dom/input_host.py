"""``<input>`` host value/checked/attribute syncing (ReactDOMInput parity subset)."""
from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import TYPE_CHECKING, Any

from .input_binding import input_host_default_from_raw

if TYPE_CHECKING:
    from .dom import ElementNode, SyntheticEvent


def _raw_type(props: Mapping[str, Any]) -> str:
    return str(props.get("type", "text")).lower()


def _has_change_listener(props: Mapping[str, Any], node: ElementNode | None = None) -> bool:
    for k in props:
        if not isinstance(k, str) or not k.startswith("on"):
            continue
        lk = k.lower()
        if lk in ("onchange", "oninput") and callable(props[k]):
            return True
    return node is not None and bool(node._listeners.get("change"))


def input_is_value_controlled(props: Mapping[str, Any], node: ElementNode | None = None) -> bool:
    return "value" in props and _has_change_listener(props, node)


def input_is_checked_controlled(props: Mapping[str, Any], node: ElementNode | None = None) -> bool:
    t = _raw_type(props)
    if t not in ("checkbox", "radio"):
        return False
    return "checked" in props and _has_change_listener(props, node)


def input_checked_from_props(props: Mapping[str, Any]) -> bool:
    if "checked" not in props:
        return bool(props.get("defaultChecked") or props.get("default_checked"))
    v = props["checked"]
    if v is None:
        return False
    return bool(v)


def input_default_checked_from_props(props: Mapping[str, Any]) -> bool:
    if "defaultChecked" in props:
        return bool(props["defaultChecked"])
    if "default_checked" in props:
        return bool(props["default_checked"])
    return input_checked_from_props(props)


def is_value_dirty(node: ElementNode) -> bool:
    if node.tag.lower() != "input":
        return False
    if node._input_value_dirty:
        return True
    if node._input_dom_value is not None:
        return True
    t = _raw_type(node.props)
    if t in ("checkbox", "radio", "submit", "reset", "button", "image"):
        return False
    if "value" not in node.props and node._input_host_default_value:
        return True
    if input_is_value_controlled(node.props, node):
        attr = node.get_attribute("value")
        dom = node.dom_input_value()
        if attr is None:
            return False
        return attr != dom
    return False


def is_checked_dirty(node: ElementNode) -> bool:
    if node.tag.lower() != "input":
        return False
    return node._input_checked_dirty or node.checked != node._input_default_checked


def assert_input_tracking_is_current(container: Any) -> None:
    """Walk inputs under ``container.root``; tracked value must match DOM value."""

    from .dom import Container, ElementNode

    assert isinstance(container, Container)

    def walk(n: Any) -> None:
        if isinstance(n, ElementNode):
            if n.tag.lower() == "input":
                tracked = n._input_tracked_value
                current = n.dom_input_value()
                t = _raw_type(n.props)
                if t in ("checkbox", "radio"):
                    current = "true" if n.checked else "false"
                    if tracked is None:
                        return
                if tracked is not None and tracked != current:
                    raise AssertionError(
                        f"Input tracking mismatch: tracked {tracked!r} vs current {current!r}"
                    )
            for ch in n.children:
                walk(ch)

    walk(container.root)


def _sync_value_attribute(node: ElementNode) -> None:
    t = _raw_type(node.props)
    if t in ("checkbox", "radio", "submit", "reset", "button", "image"):
        return
    if t in ("reset", "submit") and "value" not in node.props:
        node._input_value_attr = None
        return
    if input_is_value_controlled(node.props, node):
        if node._input_focused and t == "number":
            return
        node._input_value_attr = node.dom_input_value()
    elif node._input_host_default_value or "value" in node.props:
        node._input_value_attr = node.dom_input_value()
        node._input_value_dirty = bool(node._input_host_default_value)


def _radio_scope_root(node: ElementNode) -> ElementNode:
    cur: ElementNode = node
    while cur.parent is not None:
        if cur.parent.tag.lower() == "form":
            return cur.parent
        cur = cur.parent
    return cur.parent if cur.parent is not None else cur


def _find_radio_group(node: ElementNode) -> list[ElementNode]:
    from .dom import ElementNode as El

    name = node.props.get("name")
    if name is None:
        return [node]
    scope = _radio_scope_root(node)
    out: list[El] = []

    def walk(n: El) -> None:
        if n.tag.lower() == "input" and _raw_type(n.props) == "radio" and n.props.get("name") == name:
            out.append(n)
        for ch in n.children:
            if isinstance(ch, El):
                walk(ch)

    walk(scope)
    return out


def sync_radio_group_checked(node: ElementNode, *, checked: bool) -> None:
    if _raw_type(node.props) != "radio":
        return
    for peer in _find_radio_group(node):
        if peer is node:
            peer._input_checked_dom = checked
        else:
            peer._input_checked_dom = False
        peer._input_checked_dirty = True
        _sync_checked_attribute(peer)


def _sync_checked_attribute(node: ElementNode) -> None:
    return


def _blur_active_input_in_tree(root: ElementNode, *, except_node: ElementNode | None) -> None:
    from .dom import ElementNode as El

    def walk(n: El) -> None:
        if n is except_node:
            return
        if n.tag.lower() == "input" and n._input_focused:
            n.blur()
        for ch in n.children:
            if isinstance(ch, El):
                walk(ch)

    walk(root)


def init_input_host_on_mount(node: ElementNode) -> None:
    if node.tag.lower() != "input":
        return
    node._input_default_checked = input_default_checked_from_props(node.props)
    t = _raw_type(node.props)
    if t in ("checkbox", "radio"):
        node._input_tracked_value = "true" if node.checked else "false"
    else:
        node._input_tracked_value = node.dom_input_value()
    if t in ("checkbox", "radio"):
        node._input_checked_dirty = input_is_checked_controlled(node.props, node) or "checked" in node.props
    if t == "date" and node._input_host_default_value:
        node._input_mount_log.append("type")
        node._input_dom_value = node._input_host_default_value
        node._input_mount_log.append("value")
        node._input_mount_log.append("defaultValue")
    if input_is_value_controlled(node.props, node):
        node._input_value_attr = node.dom_input_value()
        node._input_value_dirty = t == "number"
    elif node._input_host_default_value and t not in ("checkbox", "radio", "submit", "reset"):
        node._input_value_dirty = True
        _sync_value_attribute(node)
    else:
        _sync_value_attribute(node)
    _sync_checked_attribute(node)


def sync_input_host_after_props_update(
    node: ElementNode,
    *,
    prev_props: Mapping[str, Any] | None,
    prev_host_default: str | None = None,
) -> None:
    if node.tag.lower() != "input":
        return
    t = _raw_type(node.props)
    prev_default = (
        prev_host_default
        if prev_host_default is not None
        else (input_host_default_from_raw(prev_props) if prev_props else None)
    )
    prev_dom = node.dom_input_value() if prev_props is not None else None
    user_edited_away = (
        is_value_dirty(node) and prev_default is not None and prev_dom != prev_default
    )
    if (
        prev_props is not None
        and not input_is_value_controlled(node.props, node)
        and node._input_host_default_value != prev_default
        and not user_edited_away
    ):
        node._input_dom_value = None
        node._input_value_dirty = True
        _sync_value_attribute(node)
    if t in ("reset", "submit") and "value" not in node.props:
        node._input_value_attr = None
    if input_is_value_controlled(node.props, node):
        if not (node._input_focused and t == "number"):
            _sync_value_attribute(node)
    elif is_value_dirty(node) and node._input_dom_value is not None:
        pass
    else:
        node._input_dom_value = None
    if t in ("checkbox", "radio"):
        if input_is_checked_controlled(node.props, node) or "checked" in node.props:
            node._input_checked_dom = input_checked_from_props(node.props)
        node._input_checked_dirty = True
    t = _raw_type(node.props)
    if t in ("checkbox", "radio"):
        node._input_tracked_value = "true" if node.checked else "false"
    else:
        node._input_tracked_value = node.dom_input_value()


def restore_input_on_form_reset(node: ElementNode) -> None:
    node._input_dom_value = None
    node._input_value_attr = node._input_host_default_value
    node._input_value_dirty = False
    t = _raw_type(node.props)
    if t in ("checkbox", "radio"):
        node._input_tracked_value = "true" if node.checked else "false"
    else:
        node._input_tracked_value = node.dom_input_value()


def restore_controlled_radio_group_from_props(node: ElementNode) -> None:
    if _raw_type(node.props) != "radio":
        return
    for peer in _find_radio_group(node):
        if "checked" in peer.props or input_is_checked_controlled(peer.props, peer) or _has_change_listener(
            peer.props, peer
        ):
            peer._input_checked_dom = input_checked_from_props(peer.props)
        else:
            peer._input_checked_dom = False
        peer._input_checked_dirty = True


def finish_input_event_dispatch(node: ElementNode) -> None:
    """After listeners run, restore controlled props unless still inside nested dispatch."""

    if node.tag.lower() != "input":
        return
    if input_is_value_controlled(node.props, node):
        if not (node._input_focused and _raw_type(node.props) == "number"):
            _sync_value_attribute(node)
        node._input_dom_value = None
    elif node._input_dom_value is not None and input_is_value_controlled(node.props, node):
        node._input_dom_value = None
    if _raw_type(node.props) == "radio" and _has_change_listener(node.props, node):
        restore_controlled_radio_group_from_props(node)
    elif input_is_checked_controlled(node.props, node):
        node._input_checked_dom = input_checked_from_props(node.props)
        if _raw_type(node.props) == "radio" and node.checked:
            sync_radio_group_checked(node, checked=True)
    t = _raw_type(node.props)
    if t in ("checkbox", "radio"):
        node._input_tracked_value = "true" if node.checked else "false"
    else:
        node._input_tracked_value = node.dom_input_value()


def handle_input_host_event(node: ElementNode, type_: str, invoke_listeners: Callable[[], None]) -> None:
    if node._input_in_event_dispatch:
        invoke_listeners()
        return
    node._input_in_event_dispatch = True
    try:
        _handle_input_host_event_impl(node, type_, invoke_listeners)
    finally:
        node._input_in_event_dispatch = False


def _handle_input_host_event_impl(node: ElementNode, type_: str, invoke_listeners: Callable[[], None]) -> None:
    t = _raw_type(node.props)
    if type_ == "input" and t not in ("checkbox", "radio"):
        if node._input_dom_value is None:
            node._input_dom_value = node.dom_input_value()
        node._input_value_dirty = True
        if input_is_value_controlled(node.props, node) and not (node._input_focused and t == "number"):
            _sync_value_attribute(node)
    if type_ == "blur":
        node._input_focused = False
        if input_is_value_controlled(node.props, node):
            _sync_value_attribute(node)
    if type_ == "focus":
        node._input_focused = True
    if type_ == "click" and t == "radio" and not node.props.get("disabled"):
        if node._input_checked_dom is None:
            node._input_checked_dom = True
        sync_radio_group_checked(node, checked=True)
    invoke_listeners()
    finish_input_event_dispatch(node)


def event_target_value(node: ElementNode) -> str:
    return node.dom_input_value()


def wrap_event_listener(listener: Callable[[SyntheticEvent], None]) -> Callable[[SyntheticEvent], None]:
    """Call listeners without a bound ``this`` (ReactDOMInput ``bind`` parity)."""

    def wrapped(ev: SyntheticEvent) -> None:
        listener(ev)

    return wrapped
