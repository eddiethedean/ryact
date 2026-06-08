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
    related_target: ElementNode | None = None
    _stopped: bool = False
    _default_prevented: bool = False
    submitter: ElementNode | None = None

    def stop_propagation(self) -> None:
        self._stopped = True

    def prevent_default(self) -> None:
        self._default_prevented = True

    @property
    def default_prevented(self) -> bool:
        return self._default_prevented

    @property
    def defaultPrevented(self) -> bool:
        return self._default_prevented

    @property
    def relatedTarget(self) -> ElementNode | None:
        return self.related_target


@dataclass
class ElementNode(Node):
    tag: str = "div"
    key: str | None = None
    props: dict[str, Any] = field(default_factory=dict)
    children: list[Node] = field(default_factory=list)
    _listeners: dict[str, list[Callable[[SyntheticEvent], None]]] = field(default_factory=dict)
    _listeners_capture: dict[str, list[Callable[[SyntheticEvent], None]]] = field(default_factory=dict)
    _native_event_parent: ElementNode | None = field(default=None, repr=False)
    _event_container: Container | None = field(default=None, repr=False)
    _native_blocks_submission: bool = field(default=False, repr=False)
    _current_dispatch_event: SyntheticEvent | None = field(default=None, repr=False)
    _option_value_attr: str | None = field(default=None, repr=False)
    _option_force_value_attr: bool = field(default=False, repr=False)
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
    _last_style_prop_id: int | None = field(default=None, repr=False)
    _inner_html_preserved: str | None = field(default=None, repr=False)
    _input_host_default_value: str = field(default="", repr=False)
    _input_dom_value: str | None = field(default=None, repr=False)
    _input_value_attr: str | None = field(default=None, repr=False)
    _input_value_dirty: bool = field(default=False, repr=False)
    _input_checked_dom: bool | None = field(default=None, repr=False)
    _input_checked_dirty: bool = field(default=False, repr=False)
    _input_default_checked: bool = field(default=False, repr=False)
    _input_focused: bool = field(default=False, repr=False)
    _input_tracked_value: str | None = field(default=None, repr=False)
    _delegated_change_emitted: bool = field(default=False, repr=False)
    _input_mount_log: list[str] = field(default_factory=list, repr=False)
    _input_in_event_dispatch: bool = field(default=False, repr=False)
    _input_focus_pinned_value_attr: str | None = field(default=None, repr=False)
    _host_reconcile_id: int = field(default=0, repr=False)
    _document_create_options: dict[str, Any] | None = field(default=None, repr=False)
    _form_action_fn: Callable[..., Any] | None = field(default=None, repr=False)
    _namespace_uri: str | None = field(default=None, repr=False)

    @property
    def namespaceURI(self) -> str:
        from .svg_namespace import HTML_NAMESPACE

        return self._namespace_uri or HTML_NAMESPACE

    @property
    def tagName(self) -> str:
        from .svg_namespace import host_tag_name_for_namespace

        return host_tag_name_for_namespace(tag=self.tag, namespace_uri=self.namespaceURI)

    @property
    def nodeName(self) -> str:
        return self.tag.upper()

    @property
    def onclick(self) -> Callable[[], None] | None:
        """iOS tap-highlight noop handler when ``onClick`` is registered."""

        listeners = self._listeners.get("click")
        if not listeners:
            return None

        def _noop() -> None:
            return None

        return _noop

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
        if self.tag.lower() == "option" and name.lower() == "value":
            if self._option_value_attr is not None:
                return self._option_value_attr
            if "value" in self.props:
                v = self.props["value"]
                return "" if v is None else str(v)
            return None
        if self.tag.lower() == "input" and name.lower() == "value":
            from .input_host import _raw_type

            if self._input_focused and self._input_focus_pinned_value_attr is not None:
                return self._input_focus_pinned_value_attr
            if _raw_type(self.props) in ("reset", "submit") and "value" not in self.props:
                return self._input_value_attr
            if self._input_value_attr is not None:
                return self._input_value_attr
        want = name.lower()
        for k, v in self.props.items():
            if k == "children":
                continue
            if _is_custom_element_dom_tag(self.tag):
                if str(k).lower() != want:
                    continue
            elif html_attribute_name(k).lower() != want:
                continue
            if v is None or v is False:
                return None
            if v is True:
                return ""
            return str(v)
        return None

    def getAttribute(self, name: str) -> str | None:
        return self.get_attribute(name)

    def getAttributeNS(self, namespace: str, local_name: str) -> str | None:
        from .svg_namespace import XLINK_NAMESPACE

        if namespace == XLINK_NAMESPACE and local_name == "href":
            for key in ("xlinkHref", "xlink:href"):
                v = self.props.get(key)
                if v is not None and not callable(v):
                    return str(v)
            return self.get_attribute("xlink:href")
        return self.get_attribute(local_name)

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

    def set_untracked_value(self, value: Any) -> None:
        """Test helper: assign DOM value without a React commit (upstream ``setUntrackedValue``)."""

        if self.tag.lower() != "input":
            raise TypeError("set_untracked_value is only defined for host <input> nodes")
        self._input_dom_value = "" if value is None else str(value)
        self._input_value_dirty = True

    def set_untracked_checked(self, checked: bool) -> None:
        """Test helper: assign DOM checked without a React commit."""

        if self.tag.lower() != "input":
            raise TypeError("set_untracked_checked is only defined for host <input> nodes")
        self._input_checked_dom = bool(checked)
        self._input_checked_dirty = True
        if str(self.props.get("type", "")).lower() == "radio" and checked:
            from .input_host import sync_radio_group_checked

            sync_radio_group_checked(self, checked=True)

    @property
    def checked(self) -> bool:
        if self.tag.lower() != "input":
            raise AttributeError("checked")
        if self._input_checked_dom is not None:
            return self._input_checked_dom
        from .input_host import input_checked_from_props

        return input_checked_from_props(self.props)

    @checked.setter
    def checked(self, value: bool) -> None:
        if self.tag.lower() != "input":
            raise AttributeError("checked")
        self._input_checked_dom = bool(value)
        self._input_checked_dirty = True

    def focus(self) -> None:
        from .input_host import _blur_active_input_in_tree

        root: ElementNode = self
        while root.parent is not None:
            root = root.parent
        _blur_active_input_in_tree(root, except_node=self)
        if self.tag.lower() == "input":
            from .input_host import _raw_type, input_is_value_controlled

            if input_is_value_controlled(self.props, self) and _raw_type(self.props) == "number":
                pinned = self._input_value_attr
                if pinned is None and "value" in self.props:
                    pinned = str(self.props["value"])
                self._input_focus_pinned_value_attr = pinned
        self._input_focused = True
        from .host_focus import note_host_focused

        note_host_focused(self)
        self.dispatch_event("focus")

    def blur(self) -> None:
        was_focused = self._input_focused
        self._input_focused = False
        from .host_focus import note_host_blurred

        note_host_blurred(self)
        self._input_focus_pinned_value_attr = None
        if was_focused:
            self.dispatch_event("blur")

    def click(self) -> None:
        self.dispatch_event("click")
        if self.tag.lower() in ("button", "input"):
            t = str(self.props.get("type", "")).lower()
            if t == "submit" or (self.tag.lower() == "button" and t in ("", "submit")):
                from .form_actions import trigger_submit_from_control

                trigger_submit_from_control(self)

    def reset(self) -> None:
        if self.tag.lower() != "form":
            raise AttributeError("reset")
        from .input_host import restore_input_on_form_reset

        def walk(n: Node) -> None:
            if isinstance(n, ElementNode):
                if n.tag.lower() == "input":
                    restore_input_on_form_reset(n)
                for ch in n.children:
                    walk(ch)

        walk(self)

    @property
    def elements(self) -> Any:
        from .form_data import FormElementsCollection

        if self.tag.lower() != "form":
            raise AttributeError("elements")
        return FormElementsCollection(self)

    def request_submit(self, submitter: ElementNode | None = None) -> None:
        if self.tag.lower() != "form":
            raise AttributeError("request_submit")
        from .form_actions import handle_react_form_submit

        handle_react_form_submit(self, submitter=submitter)

    def requestSubmit(self, submitter: ElementNode | None = None) -> None:
        self.request_submit(submitter)

    def submit(self) -> None:
        if self.tag.lower() != "form":
            raise AttributeError("submit")
        from .form_actions import _REACT_MANAGED_FORMS, unexpected_manual_submit_error

        if id(self) in _REACT_MANAGED_FORMS:
            raise unexpected_manual_submit_error()
        from .form_actions import _navigate_to, resolve_form_action

        resolved = resolve_form_action(self, None)
        if isinstance(resolved, str):
            _navigate_to(resolved)

    def dom_input_value(self) -> str:
        """``HTMLInputElement.value`` subset: checkbox/radio with no ``value`` prop resolve to ``on``.

        Integer-valued floats (e.g. ``0.0``) stringify like React text inputs (``\"0\"``).
        """

        if self.tag.lower() != "input":
            raise TypeError("dom_input_value is only defined for host <input> nodes")
        if self._input_dom_value is not None:
            return self._input_dom_value
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

    def dispatch_event(self, type_: str, *, related_target: ElementNode | None = None) -> None:
        from .event_listener import dispatch_host_event
        from .input_host import handle_input_host_event, wrap_event_listener

        event = SyntheticEvent(type=type_, target=self, related_target=related_target)
        self._current_dispatch_event = event
        is_input_host = self.tag.lower() == "input"

        delegates_change = _input_delegates_change_on_input_event(self.tag, self.props)
        delegate_change_with_input = type_ == "input" and delegates_change
        suppress_ancestor_native_change_bubble = (
            type_ == "change" and not _native_change_bubbles_onchange_listeners_to_ancestors(self.tag)
        )
        suppress_duplicate_delegated_change = (
            type_ == "change"
            and delegates_change
            and _input_or_textarea_host(self.tag)
            and self._delegated_change_emitted
        )

        def skip_listeners(node: ElementNode) -> bool:
            if type_ != "change":
                return False
            if suppress_duplicate_delegated_change:
                return True
            return suppress_ancestor_native_change_bubble and node is not self

        def after_listeners() -> None:
            if delegate_change_with_input:
                node: ElementNode | None = self
                while node is not None:
                    ch_ev = SyntheticEvent(type="change", target=self)
                    ch_ev.current_target = node
                    for listener in node._listeners.get("change", []):
                        wrap_event_listener(listener)(ch_ev)
                        if ch_ev._stopped:
                            return
                    node = node.parent
                self._delegated_change_emitted = True
            if (
                type_ == "click"
                and self.tag.lower() == "input"
                and str(self.props.get("type", "")).lower() == "radio"
                and not event._stopped
            ):
                ch_ev = SyntheticEvent(type="change", target=self)
                ch_ev.current_target = self
                for listener in self._listeners.get("change", []):
                    wrap_event_listener(listener)(ch_ev)
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

        def run_dispatch() -> None:
            dispatch_host_event(self, type_, skip_listeners=skip_listeners, after_listeners=after_listeners)

        try:
            if is_input_host:
                handle_input_host_event(self, type_, run_dispatch)
            else:
                run_dispatch()
        finally:
            if type_ == "change" and self._delegated_change_emitted:
                self._delegated_change_emitted = False
            self._current_dispatch_event = None

    @property
    def value(self) -> str:
        """DOM-like ``HTMLInputElement`` / ``HTMLSelectElement`` / ``HTMLTextAreaElement.value`` subset."""

        tl = self.tag.lower()
        if tl == "input":
            return self.dom_input_value()
        if tl == "select":
            return _select_get_value(self)
        if tl == "textarea":
            return self.dom_textarea_value()
        if tl == "option":
            if self._option_value_attr is not None:
                return self._option_value_attr
            if self.children and isinstance(self.children[0], TextNode):
                return self.children[0].text
            return ""
        raise AttributeError("value")

    @property
    def selectedIndex(self) -> int:
        if self.tag.lower() != "select":
            raise AttributeError("selectedIndex")
        opts: list[ElementNode] = []
        _collect_select_option_nodes(self, opts)
        for i, opt in enumerate(opts):
            if opt.props.get("selected"):
                return i
        return 0

    @value.setter
    def value(self, v: Any) -> None:
        tl = self.tag.lower()
        if tl == "input":
            self.set_untracked_value(v)
            return
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
    _is_document_fragment: bool = field(default=False, repr=False)
    # DEV HTML nesting: implicit host parent when the mount node is not modeled (e.g. ``<p>`` shell).
    dom_nesting_mount_tag: str | None = None
    _ryact_dom_root: Any = field(default=None, repr=False)
    _ios_tap_onclick: Callable[[], None] | None = field(default=None, repr=False)
    _form_status_snapshot: Any = field(default=None, repr=False)

    @property
    def onclick(self) -> Callable[[], None] | None:
        return self._ios_tap_onclick

    @property
    def text_content(self) -> str:
        """Concatenated text of host descendants (``textContent`` parity for tests)."""

        parts: list[str] = []

        def walk(n: Node) -> None:
            if isinstance(n, TextNode):
                parts.append(n.text)
            elif isinstance(n, ElementNode):
                for ch in n.children:
                    walk(ch)

        for ch in self.root.children:
            walk(ch)
        return "".join(parts)

    @classmethod
    def create_document_fragment(cls) -> Container:
        """Detached mount target (``document.createDocumentFragment`` parity)."""

        return cls(_is_document_fragment=True)

    def adopt_children_from(self, other: Container) -> None:
        """Move React host children from ``other`` into this container (fragment append)."""

        for ch in list(other.root.children):
            self.root.children.append(ch)
            ch.parent = self.root
        other.root.children.clear()

    def query_selector_all(self, selector: str) -> list[ElementNode]:
        """Minimal ``querySelectorAll`` for tests (``input``, ``input[name=…]``)."""

        if selector.strip() != "input":
            raise ValueError(f"unsupported selector: {selector!r}")
        out: list[ElementNode] = []

        def walk(n: Node) -> None:
            if isinstance(n, ElementNode):
                if n.tag.lower() == "input":
                    out.append(n)
                for ch in n.children:
                    walk(ch)

        walk(self.root)
        return out


