from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

from ryact_testkit.interop import InteropRunner

from .html_props import _is_custom_element_dom_tag


def _input_or_textarea_host(tag: str) -> bool:
    return tag.lower() in ("input", "textarea")


def _input_delegates_change_on_input_event(tag: str, props: Mapping[str, Any]) -> bool:
    """Text-like ``<input>`` (not ``type=radio``) and ``<textarea>`` get delegated ``onChange`` from ``input``."""

    tl = tag.lower()
    if tl == "textarea":
        return True
    if tl != "input":
        return False
    return str(props.get("type", "text")).lower() != "radio"


def _native_change_bubbles_onchange_listeners_to_ancestors(tag: str) -> bool:
    """Whether a native ``change`` from this host may invoke ancestor ``change`` listeners (React)."""

    t = tag.lower()
    if _is_custom_element_dom_tag(t):
        return True
    return t in {"input", "textarea", "select"}


def _option_value_str(opt: ElementNode) -> str:
    v = opt.props.get("value")
    if v is None and opt.children and isinstance(opt.children[0], TextNode):
        v = opt.children[0].text
    return "" if v is None else str(v)


def _collect_select_option_nodes(host: ElementNode, out: list[ElementNode]) -> None:
    for ch in host.children:
        if not isinstance(ch, ElementNode):
            continue
        tl = ch.tag.lower()
        if tl == "option":
            out.append(ch)
        elif tl == "optgroup":
            _collect_select_option_nodes(ch, out)


def _select_get_value(host: ElementNode) -> str:
    opts: list[ElementNode] = []
    _collect_select_option_nodes(host, opts)
    for opt in opts:
        if opt.props.get("selected"):
            return _option_value_str(opt)
    return ""


def _select_set_value(host: ElementNode, s: str) -> None:
    opts: list[ElementNode] = []
    _collect_select_option_nodes(host, opts)
    for opt in opts:
        if _option_value_str(opt) == s:
            opt.props["selected"] = True
        else:
            opt.props.pop("selected", None)


@dataclass
class Node:
    parent: ElementNode | None = None


@dataclass
class TextNode(Node):
    text: str = ""


@dataclass
class SyntheticEvent:
    type: str
    target: ElementNode
    current_target: ElementNode | None = None
    _stopped: bool = False

    def stop_propagation(self) -> None:
        self._stopped = True


@dataclass
class ElementNode(Node):
    tag: str = "div"
    key: str | None = None
    props: dict[str, Any] = field(default_factory=dict)
    children: list[Node] = field(default_factory=list)
    _listeners: dict[str, list[Callable[[SyntheticEvent], None]]] = field(default_factory=dict)
    # When set, callable ``on*`` listeners for these event types mirror React's ``in``-heuristic
    # (DOMPropertyOperations): the corresponding prop remains on the host as ``None`` while a
    # listener is installed, strings are kept as plain props, and removals surface as missing keys.
    custom_on_listener_property_modes: frozenset[str] = field(default_factory=frozenset)

    def append_child(self, node: Node) -> None:
        node.parent = self
        self.children.append(node)

    def add_event_listener(self, type_: str, listener: Callable[[SyntheticEvent], None]) -> None:
        self._listeners.setdefault(type_, []).append(listener)

    def set_custom_on_listener_property_mode(self, *lowercase_event_types: str) -> None:
        """Opt into React DOM ``defineProperty`` / ``in``-style handling for these custom ``on*`` events."""

        self.custom_on_listener_property_modes = frozenset(e.lower() for e in lowercase_event_types)

    def dispatch_event(self, type_: str) -> None:
        event = SyntheticEvent(type=type_, target=self)
        # Bubble from target up to root.
        node: ElementNode | None = self
        delegate_change_with_input = type_ == "input" and _input_delegates_change_on_input_event(
            self.tag, self.props
        )
        suppress_entire_native_change_primary_bubble = type_ == "change" and _input_or_textarea_host(self.tag)
        suppress_ancestor_native_change_bubble = (
            type_ == "change" and not _native_change_bubbles_onchange_listeners_to_ancestors(self.tag)
        )
        while node is not None:
            event.current_target = node
            skip_primary = False
            if type_ == "change":
                skip_primary = suppress_entire_native_change_primary_bubble or (
                    suppress_ancestor_native_change_bubble and node is not self
                )
            if not skip_primary:
                for listener in node._listeners.get(type_, []):
                    listener(event)
                    if event._stopped:
                        return
            if delegate_change_with_input:
                ch_ev = SyntheticEvent(type="change", target=self)
                ch_ev.current_target = node
                for listener in node._listeners.get("change", []):
                    listener(ch_ev)
                    if ch_ev._stopped:
                        return
            node = node.parent
        if (
            type_ == "click"
            and self.tag.lower() == "input"
            and str(self.props.get("type", "")).lower() == "radio"
            and not event._stopped
        ):
            ch_ev = SyntheticEvent(type="change", target=self)
            ch_ev.current_target = self
            for listener in self._listeners.get("change", []):
                listener(ch_ev)
                if ch_ev._stopped:
                    return
        if (
            type_ == "change"
            and self.tag.lower() == "select"
            and "value" in self.props
            and self.parent is not None
            and self in self.parent.children
        ):
            from .select_binding import sync_host_select_controlled_selection

            sync_host_select_controlled_selection(self)

    @property
    def value(self) -> str:
        """DOM-like ``HTMLSelectElement.value`` (single select subset)."""

        if self.tag.lower() != "select":
            raise AttributeError("value")
        return _select_get_value(self)

    @value.setter
    def value(self, v: Any) -> None:
        if self.tag.lower() != "select":
            raise AttributeError("value")
        _select_set_value(self, "" if v is None else str(v))

    @property
    def innerHTML(self) -> str:
        # Minimal surface for dangerouslySetInnerHTML client tests.
        return str(self.props.get("innerHTML", ""))


@dataclass
class Container:
    root: ElementNode = field(default_factory=lambda: ElementNode(tag="root"))
    ops: list[dict[str, Any]] = field(default_factory=list)
    interop_runner: InteropRunner | None = None
    # DEV HTML nesting: implicit host parent when the mount node is not modeled (e.g. ``<p>`` shell).
    dom_nesting_mount_tag: str | None = None
