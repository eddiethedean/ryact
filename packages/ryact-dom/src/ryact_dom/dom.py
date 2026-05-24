from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

from ryact_testkit.interop import InteropRunner

from .host_style import HostStyleDeclaration
from .html_props import _is_custom_element_dom_tag, html_attribute_name

_host_reconcile_id_counter = 123


def allocate_host_reconcile_id() -> int:
    """Monotonic id assigned when a host node is first created (MultiChildReconcile parity)."""

    global _host_reconcile_id_counter
    n = _host_reconcile_id_counter
    _host_reconcile_id_counter += 1
    return n


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
    # When a prop key disappears from React updates, map that key to the value to assign on the
    # host (``None``, ``""``, …) instead of deleting the key — mirrors ``deleteValueForProperty``
    # for custom elements with property setters (opt-in; see tests).
    _custom_property_removed_values: dict[str, Any] = field(default_factory=dict, repr=False)
    # Pinned attribute values for ``get_attribute`` while ``props`` update (custom + setter parity).
    _dom_attribute_pins: dict[str, str] = field(default_factory=dict, repr=False)
    # ``<textarea>`` controlled / ``defaultValue`` host state (ReactDOMTextarea subset).
    _textarea_controlled: bool = field(default=False, repr=False)
    _textarea_host_default_value: str = field(default="", repr=False)
    _host_style: dict[str, str] = field(default_factory=dict, repr=False)
    _inner_html_preserved: str | None = field(default=None, repr=False)
    _input_host_default_value: str = field(default="", repr=False)
    _host_reconcile_id: int = field(default=0, repr=False)

    def append_child(self, node: Node) -> None:
        node.parent = self
        self.children.append(node)

    def add_event_listener(self, type_: str, listener: Callable[[SyntheticEvent], None]) -> None:
        self._listeners.setdefault(type_, []).append(listener)

    def set_custom_on_listener_property_mode(self, *lowercase_event_types: str) -> None:
        """Opt into React DOM ``defineProperty`` / ``in``-style handling for these custom ``on*`` events."""

        self.custom_on_listener_property_modes = frozenset(e.lower() for e in lowercase_event_types)

    def register_custom_property_removed_value(self, prop: str, value: Any) -> None:
        """When ``prop`` is later removed from React props, assign ``value`` instead of dropping the key."""

        self._custom_property_removed_values[prop] = value

    def pin_dom_attribute_value(self, attr_name: str, value: str) -> None:
        """Pin ``get_attribute(attr_name)`` while ``props`` may change (simulates DOM ``defineProperty``)."""

        self._dom_attribute_pins[attr_name.lower()] = value

    def get_attribute(self, name: str) -> str | None:
        """Return a pinned attribute string, or ``None`` if ``name`` is not pinned on this host."""

        pinned = self._dom_attribute_pins.get(name.lower())
        if pinned is not None:
            return pinned
        want = name.lower()
        for k, v in self.props.items():
            if k == "children":
                continue
            if html_attribute_name(k).lower() != want:
                continue
            if v is None or v is False:
                return None
            if v is True:
                return ""
            return str(v)
        return None

    def getAttribute(self, name: str) -> str | None:
        return self.get_attribute(name)

    def has_attribute(self, name: str) -> bool:
        return self.get_attribute(name) is not None

    def hasAttribute(self, name: str) -> bool:
        return self.has_attribute(name)

    @property
    def className(self) -> str:
        v = self.props.get("className")
        if v is None:
            v = self.props.get("class")
        if v is None:
            return ""
        return str(v)

    @className.setter
    def className(self, value: str) -> None:
        self.props["className"] = value

    @property
    def style(self) -> HostStyleDeclaration:
        return HostStyleDeclaration(self)

    def dom_input_value(self) -> str:
        """``HTMLInputElement.value`` subset: checkbox/radio with no ``value`` prop resolve to ``on``.

        Integer-valued floats (e.g. ``0.0``) stringify like React text inputs (``\"0\"``).
        """

        if self.tag.lower() != "input":
            raise TypeError("dom_input_value is only defined for host <input> nodes")
        t = str(self.props.get("type", "text")).lower()
        if "value" in self.props:
            v = self.props["value"]
            if v is None:
                return ""
            if isinstance(v, bool):
                return "true" if v else "false"
            if isinstance(v, float) and v == v and v == int(v):
                return str(int(v))
            return str(v)
        if t in ("checkbox", "radio"):
            return "on"
        return ""

    def dom_textarea_value(self) -> str:
        if self.tag.lower() != "textarea":
            raise TypeError("dom_textarea_value is only defined for host <textarea> nodes")
        if self.children and isinstance(self.children[0], TextNode):
            return self.children[0].text
        return ""

    @property
    def default_value(self) -> str:
        tl = self.tag.lower()
        if tl == "textarea":
            return self._textarea_host_default_value
        if tl == "input":
            return self._input_host_default_value
        raise AttributeError("default_value")

    @default_value.setter
    def default_value(self, v: str) -> None:
        tl = self.tag.lower()
        if tl == "textarea":
            self._textarea_host_default_value = "" if v is None else str(v)
            return
        if tl == "input":
            self._input_host_default_value = "" if v is None else str(v)
            return
        raise AttributeError("default_value")

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
        """DOM-like ``HTMLSelectElement.value`` / ``HTMLTextAreaElement.value`` subset."""

        tl = self.tag.lower()
        if tl == "select":
            return _select_get_value(self)
        if tl == "textarea":
            return self.dom_textarea_value()
        raise AttributeError("value")

    @value.setter
    def value(self, v: Any) -> None:
        tl = self.tag.lower()
        if tl == "select":
            _select_set_value(self, "" if v is None else str(v))
            return
        if tl == "textarea":
            s = "" if v is None else str(v)
            if self.children and isinstance(self.children[0], TextNode):
                self.children[0].text = s
            elif s:
                self.append_child(TextNode(text=s))
            return
        raise AttributeError("value")

    @property
    def innerHTML(self) -> str:
        if self._inner_html_preserved is not None:
            return self._inner_html_preserved
        if "innerHTML" in self.props:
            return str(self.props["innerHTML"])
        parts: list[str] = []
        for ch in self.children:
            if isinstance(ch, TextNode):
                parts.append(ch.text)
        return "".join(parts)

    @innerHTML.setter
    def innerHTML(self, value: str) -> None:
        self._inner_html_preserved = str(value)


@dataclass
class Container:
    root: ElementNode = field(default_factory=lambda: ElementNode(tag="root"))
    ops: list[dict[str, Any]] = field(default_factory=list)
    interop_runner: InteropRunner | None = None
    # DEV HTML nesting: implicit host parent when the mount node is not modeled (e.g. ``<p>`` shell).
    dom_nesting_mount_tag: str | None = None
