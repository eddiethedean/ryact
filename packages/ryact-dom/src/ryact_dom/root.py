from __future__ import annotations

import warnings
from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from typing import Any, Optional, Union, cast

from ryact.concurrent import Fragment, Portal
from ryact.dev import is_dev
from ryact.element import UNDEFINED, Element, create_element, props_for_component_render, raw_element_ref
from ryact.hooks import _render_component
from ryact.reconciler import (
    DEFAULT_LANE,
    Lane,
    Update,
    bind_commit,
    perform_work,
    schedule_update_on_root,
)
from ryact.reconciler import (
    create_root as create_reconciler_root,
)
from ryact.wrappers import ForwardRefType, MemoType
from schedulyr import Scheduler

from .dom import Container, ElementNode, Node, TextNode, allocate_host_reconcile_id
from .host_style import sync_host_style_from_props
from .html_props import (
    _dom_prop_lookup_key,
    _is_custom_element_dom_tag,
    _merge_class_values,
    dom_event_type_for_listener_key,
    is_event_listener_prop,
    normalize_host_prop_dict,
    warn_intrinsic_html_tag_casing_dev,
)
from .input_binding import input_host_default_from_raw, preserve_value_on_invalid_form_field_inplace
from .intrinsic_tag_dev import (
    format_dangerously_inner_html_value_dev,
    warn_unrecognized_host_tag_dev,
)
from .mount_validation import prepare_host_mount_props, void_element_children_or_innerhtml_error
from .select_binding import process_select_element_children, strip_select_internal_props
from .tag_sanitization import validate_host_intrinsic_tag_name
from .textarea_binding import process_textarea_element_children, strip_textarea_internal_props
from .validate_dom_nesting import (
    AncestorInfoDev,
    initial_ancestor_info_dev,
    updated_ancestor_info_dev,
    validate_dom_nesting_host_child_dev,
    validate_text_nesting_dev,
)

Renderable = Union[Element, str, int, float, None]


def _iter_visible_host_children(children: object) -> list[object]:
    """Expand host ``children`` like React (skip null/false; flatten arrays; accept iterables)."""

    if children is None:
        return []
    if isinstance(children, (str, bytes)):
        return [children]
    if isinstance(children, (list, tuple)):
        work: list[object] = list(children)
    elif hasattr(children, "__iter__") and not isinstance(children, Mapping):
        work = list(children)
    else:
        work = [children]
    out: list[object] = []
    for c in work:
        if c is None or c is False:
            continue
        if isinstance(c, (list, tuple)):
            out.extend(_iter_visible_host_children(c))
        else:
            out.append(c)
    return out


def _host_props_normalized(props: Mapping[str, Any], tag: str) -> dict[str, Any]:
    return normalize_host_prop_dict(prepare_host_mount_props(props, tag=tag), tag=tag)


def _raw_has_explicit_non_null_value(raw: Mapping[str, Any]) -> bool:
    """Whether ``value`` is supplied as a controlled prop (not ``None`` / ``UNDEFINED``)."""

    if "value" not in raw:
        return False
    v = raw["value"]
    return v is not UNDEFINED and v is not None


def _read_only_truthy_host(raw: Mapping[str, Any]) -> bool:
    ro = raw.get("readOnly")
    if ro is None:
        ro = raw.get("read_only")
    return ro is True or ro == ""


def _disabled_truthy_host(raw: Mapping[str, Any]) -> bool:
    d = raw.get("disabled")
    return d is True or d == "" or d == "disabled"


def _has_change_or_input_listener(raw: Mapping[str, Any]) -> bool:
    for k, v in raw.items():
        if k == "children" or not callable(v):
            continue
        et = dom_event_type_for_listener_key(k)
        if et in ("change", "input"):
            return True
    return False


def _raw_input_type_lower(raw: Mapping[str, Any]) -> str:
    return str(raw.get("type", "text")).lower()


def _raw_has_value_and_default_value(raw: Mapping[str, Any]) -> bool:
    return "value" in raw and ("defaultValue" in raw or "default_value" in raw)


def _raw_has_checked_and_default_checked(raw: Mapping[str, Any]) -> bool:
    return "checked" in raw and ("defaultChecked" in raw or "default_checked" in raw)


def _warn_host_value_and_default_value_both_dev(*, tag_l: str, raw: Mapping[str, Any]) -> None:
    """DEV: ``value`` and ``defaultValue`` together (ReactDOMInput / ReactDOMTextarea)."""

    if not is_dev():
        return
    if tag_l not in ("input", "textarea"):
        return
    if not _raw_has_value_and_default_value(raw):
        return
    if tag_l == "input" and _raw_input_type_lower(raw) in ("checkbox", "radio"):
        return
    if tag_l == "textarea":
        warnings.warn(
            "A component contains a textarea with both value and defaultValue props. "
            "Textarea elements must be either controlled or uncontrolled "
            "(specify either the value prop, or the defaultValue prop, but not "
            "both). Decide between using a controlled or uncontrolled textarea "
            "and remove one of these props. More info: "
            "https://react.dev/link/controlled-components\n"
            "    in textarea",
            UserWarning,
            stacklevel=5,
        )
        return
    t = _raw_input_type_lower(raw)
    warnings.warn(
        f"A component contains an input of type {t} with both value and defaultValue props. "
        "Input elements must be either controlled or uncontrolled "
        "(specify either the value prop, or the defaultValue prop, but not "
        "both). Decide between using a controlled or uncontrolled input "
        "element and remove one of these props. More info: "
        "https://react.dev/link/controlled-components\n"
        "    in input",
        UserWarning,
        stacklevel=5,
    )


def _warn_input_checked_and_default_checked_both_dev(*, raw: Mapping[str, Any]) -> None:
    """DEV: ``checked`` and ``defaultChecked`` together on checkbox/radio (ReactDOMInput)."""

    if not is_dev():
        return
    if not _raw_has_checked_and_default_checked(raw):
        return
    t = _raw_input_type_lower(raw)
    if t not in ("checkbox", "radio"):
        return
    warnings.warn(
        f"A component contains an input of type {t} with both checked and defaultChecked props. "
        "Input elements must be either controlled or uncontrolled "
        "(specify either the checked prop, or the defaultChecked prop, but not "
        "both). Decide between using a controlled or uncontrolled input "
        "element and remove one of these props. More info: "
        "https://react.dev/link/controlled-components\n"
        "    in input",
        UserWarning,
        stacklevel=5,
    )


def _warn_controlled_checked_missing_change_handler_dev(*, raw: Mapping[str, Any]) -> None:
    """DEV: ``checked`` on checkbox/radio without ``onChange`` / ``onInput`` / ``readOnly``."""

    if not is_dev():
        return
    if _raw_input_type_lower(raw) not in ("checkbox", "radio"):
        return
    if _raw_has_checked_and_default_checked(raw):
        return
    if "checked" not in raw:
        return
    v = raw["checked"]
    if v is UNDEFINED or v is None:
        return
    if _read_only_truthy_host(raw):
        return
    if _has_change_or_input_listener(raw):
        return
    warnings.warn(
        "You provided a `checked` prop to a form field without an `onChange` handler. "
        "This will render a read-only field. If the field should be mutable use `defaultChecked`. "
        "Otherwise, set either `onChange` or `readOnly`.\n"
        "    in input",
        UserWarning,
        stacklevel=5,
    )


def _input_is_checkbox_or_radio(*, tag_l: str, props: Mapping[str, Any]) -> bool:
    return tag_l == "input" and _raw_input_type_lower(props) in ("checkbox", "radio")


def _input_had_change_listener(node: ElementNode) -> bool:
    return bool(node._listeners.get("change") or node._listeners.get("input"))


def _input_had_value_controlled(node: ElementNode) -> bool:
    return "value" in node.props and _input_had_change_listener(node)


def _input_had_checked_controlled(node: ElementNode) -> bool:
    return "checked" in node.props and _input_had_change_listener(node)


def _host_update_prop_unchanged(node: ElementNode, key: str, new_val: Any) -> bool:
    """Whether an incremental update can skip ``updateProps`` for ``key`` (React DOMPropertyOperations)."""

    old = node.props.get(key)
    if old == new_val:
        return True
    lk = _dom_prop_lookup_key(key)
    if lk in ("class", "classname"):
        old_merged = _merge_class_values(
            node.props.get("class"),
            node.props.get("className"),
            node.props.get("class_name"),
        )
        if isinstance(new_val, str):
            return old_merged == _merge_class_values(new_val)
    if lk == "muted" and isinstance(old, bool) and isinstance(new_val, bool):
        return old is new_val
    if node.tag.lower() == "input" and lk == "value" and "change" in node._listeners:
        return old is not None and new_val is not None and str(old) == str(new_val)
    return False


def _warn_controlled_input_missing_change_handler_dev(*, tag_l: str, raw: Mapping[str, Any]) -> None:
    """DEV: ``value`` without ``onChange`` / ``onInput`` / ``readOnly`` (ReactDOMInput)."""

    if not is_dev():
        return
    if tag_l not in ("input", "textarea"):
        return
    if _raw_has_value_and_default_value(raw):
        return
    if not _raw_has_explicit_non_null_value(raw):
        return
    if _read_only_truthy_host(raw) or _disabled_truthy_host(raw):
        return
    if _has_change_or_input_listener(raw):
        return
    warnings.warn(
        "You provided a `value` prop to a form field without an `onChange` handler. "
        "This will render a read-only field. If the field should be mutable use `defaultValue`. "
        "Otherwise, set either `onChange` or `readOnly`.\n"
        f"    in {tag_l}",
        UserWarning,
        stacklevel=5,
    )


_VOID_TAGS: frozenset[str] = frozenset(
    {
        "area",
        "base",
        "br",
        "col",
        "embed",
        "hr",
        "img",
        "input",
        "keygen",
        "link",
        "meta",
        "param",
        "source",
        "track",
        "wbr",
        "menuitem",
    }
)

_dom_component_stack: list[str] = []


class _StackFrame:
    def __init__(self, name: str) -> None:
        self._name = name

    def __enter__(self) -> None:
        _dom_component_stack.append(self._name)

    def __exit__(self, exc_type, exc, tb) -> bool | None:
        if _dom_component_stack and _dom_component_stack[-1] == self._name:
            _dom_component_stack.pop()
        return None


def _dom_stack_str() -> str:
    from ryact.devtools import format_component_stack

    # React-ish: innermost last; we record push on call so stack is outer->inner.
    return format_component_stack(list(_dom_component_stack))


def _op(container: Container, payload: dict[str, object]) -> None:
    container.ops.append(payload)


@dataclass(frozen=True)
class RenderedText:
    text: str


@dataclass(frozen=True, kw_only=True)
class RenderedElement:
    tag: str
    key: str | None
    props: dict[str, Any]
    listeners: dict[str, list[Callable[[Any], None]]]
    owner_stack: str
    custom_on_property_mode: frozenset[str] = frozenset()
    textarea_controlled: bool = False
    textarea_host_default_value: str = ""
    input_host_default_value: str | None = None
    children: list[RenderedNode]


RenderedNode = RenderedText | RenderedElement


def _lookup_host_element_at_path(container: Container, path: tuple[int, ...]) -> ElementNode | None:
    node: Node = container.root
    for idx in path:
        if not isinstance(node, ElementNode):
            return None
        ch = node.children
        if idx < 0 or idx >= len(ch):
            return None
        node = ch[idx]
    return node if isinstance(node, ElementNode) else None


def _detach_host_subtree(node: Node) -> None:
    if isinstance(node, ElementNode):
        for ch in list(node.children):
            _detach_host_subtree(ch)
        node.children.clear()
    node.parent = None


def _render_to_virtual(
    node: Renderable,
    *,
    portal_targets: list[Any],
    container: Container | None = None,
    parent_host_tag: str | None = None,
    ancestor_info: AncestorInfoDev | None = None,
    host_parent_path: tuple[int, ...] = (),
    next_child_index: list[int] | None = None,
) -> list[RenderedNode]:
    if node is None:
        return []
    if isinstance(node, (str, int, float)):
        return [RenderedText(text=str(node))]
    if not isinstance(node, Element):
        raise TypeError(f"Unsupported node type: {type(node)!r}")

    if ancestor_info is None:
        ancestor_info = initial_ancestor_info_dev(container)

    # Host element
    if isinstance(node.type, str):
        if node.type in ("__js_subtree__", "__py_subtree__"):
            if container is None or container.interop_runner is None:
                raise RuntimeError(
                    "Interop boundary encountered but no interop_runner is configured on the DOM container."
                )
            runner = container.interop_runner
            boundary_id = "dom"  # deterministic, host-owned (can be refined later)
            props = node.props.get("props") if isinstance(node.props, Mapping) else None
            children = node.props.get("children", ()) if isinstance(node.props, Mapping) else ()
            if node.type == "__js_subtree__":
                module_id = str(node.props.get("module_id"))
                export = str(node.props.get("export", "default"))
                rendered = runner.render_js(
                    module_id=module_id,
                    export=export,
                    props=cast(dict[str, object] | None, props),
                    children=cast(tuple[object, ...], children),
                    boundary_id=boundary_id,
                )
            else:
                component_id = str(node.props.get("component_id"))
                rendered = runner.render_py(
                    component_id=component_id,
                    props=cast(dict[str, object] | None, props),
                    children=cast(tuple[object, ...], children),
                    boundary_id=boundary_id,
                )
            return _render_to_virtual(
                cast(Renderable, rendered),
                portal_targets=portal_targets,
                container=container,
                parent_host_tag=parent_host_tag,
                ancestor_info=ancestor_info,
                host_parent_path=host_parent_path,
                next_child_index=next_child_index,
            )
        if node.type == Fragment:
            out: list[RenderedNode] = []
            children = node.props.get("children", ())
            for c in children:
                out.extend(
                    _render_to_virtual(
                        c,
                        portal_targets=portal_targets,
                        container=container,
                        parent_host_tag=parent_host_tag,
                        ancestor_info=ancestor_info,
                        host_parent_path=host_parent_path,
                        next_child_index=next_child_index,
                    )
                )
            return out
        if node.type == Portal:
            target = node.props.get("container")
            if target is not None:
                if container is None:
                    raise RuntimeError("Portal rendering requires a host Container (ops + reconciliation context).")
                if target not in portal_targets:
                    portal_targets.append(target)
                assert hasattr(target, "root")
                next_portal: list[RenderedNode] = []
                portal_child_index = [0]
                children = node.props.get("children", ())
                for c in children:
                    next_portal.extend(
                        _render_to_virtual(
                            c,
                            portal_targets=portal_targets,
                            container=container,
                            parent_host_tag=parent_host_tag,
                            ancestor_info=ancestor_info,
                            host_parent_path=(),
                            next_child_index=portal_child_index,
                        )
                    )
                _commit_children(
                    container=container,
                    parent=target.root,
                    next_children=next_portal,
                    path=[],
                    owner_stack="",
                )
            return []

        validate_host_intrinsic_tag_name(node.type)
        if is_dev():
            warn_intrinsic_html_tag_casing_dev(node.type, parent_host_tag)
            warn_unrecognized_host_tag_dev(node.type, parent_host_tag)
        tag_l = node.type.lower()
        path_enabled = next_child_index is not None
        if path_enabled:
            slot = next_child_index[0]
            next_child_index[0] += 1
            my_host_path = host_parent_path + (slot,)
        else:
            my_host_path = None
        if is_dev():
            validate_dom_nesting_host_child_dev(
                child_tag=tag_l,
                ancestor_info=ancestor_info,
                component_stack=_dom_stack_str(),
            )
        info_inside = updated_ancestor_info_dev(ancestor_info, tag_l)
        is_custom_el = _is_custom_element_dom_tag(node.type)
        raw_map = dict(node.props) if isinstance(node.props, Mapping) else {}
        host_in_prev = None
        if tag_l == "input" and path_enabled and container is not None and my_host_path is not None:
            cand = _lookup_host_element_at_path(container, my_host_path)
            if cand is not None and cand.tag.lower() == "input":
                host_in_prev = cand
                preserve_value_on_invalid_form_field_inplace(raw_map, host_in_prev)
        props = _host_props_normalized(raw_map, node.type)
        dsh = props.get("dangerouslySetInnerHTML") or props.get("dangerously_set_inner_html")
        if tag_l in _VOID_TAGS and tag_l != "menuitem":
            if isinstance(dsh, dict) and dsh.get("__html") is not None:
                raise void_element_children_or_innerhtml_error(node.type)
            if node.props.get("children", ()):
                raise void_element_children_or_innerhtml_error(node.type)
        listeners: dict[str, list[Callable[[Any], None]]] = {}
        custom_on_property_mode: frozenset[str] = frozenset()
        if is_custom_el and path_enabled and container is not None and my_host_path is not None:
            prev_host = _lookup_host_element_at_path(container, my_host_path)
            if prev_host is not None and prev_host.tag == node.type:
                custom_on_property_mode = prev_host.custom_on_listener_property_modes
        for prop, value in list(props.items()):
            event_type = dom_event_type_for_listener_key(prop)
            if event_type is None:
                continue
            # Custom elements: do not treat non-function `on*` props as listeners.
            # (React keeps these as plain attributes/properties.)
            if is_custom_el and not callable(value):
                continue
            # InvalidEventListeners slice:
            # - null/None listeners should be ignored
            # - non-callable listeners should be prevented at dispatch time
            if value is None:
                del props[prop]
                continue
            if is_event_listener_prop(prop, value):
                listeners.setdefault(event_type, []).append(cast(Callable[[Any], None], value))
                if is_custom_el and event_type in custom_on_property_mode:
                    props[prop] = None
                else:
                    del props[prop]
                continue

            # Non-function listener: attach a sentinel that raises when dispatched.
            def _raise(_evt: Any, v=value, p=prop) -> None:
                raise TypeError(f"Expected `{p}` listener to be a function, instead got {type(v)!r}")

            listeners.setdefault(event_type, []).append(_raise)
            del props[prop]

        raw_host = raw_map if tag_l == "input" else (dict(node.props) if isinstance(node.props, Mapping) else {})
        if tag_l in ("input", "textarea"):
            _warn_host_value_and_default_value_both_dev(tag_l=tag_l, raw=raw_host)
            if tag_l == "input":
                _warn_input_checked_and_default_checked_both_dev(raw=raw_host)
                _warn_controlled_checked_missing_change_handler_dev(raw=raw_host)
            _warn_controlled_input_missing_change_handler_dev(tag_l=tag_l, raw=raw_host)
        children = node.props.get("children", ())
        textarea_controlled = False
        textarea_host_default_value = ""
        input_host_default_value: str | None = None
        if tag_l == "input":
            input_host_default_value = input_host_default_from_raw(raw_host)
        if tag_l == "select":
            host_sel_prev = None
            if path_enabled and container is not None and my_host_path is not None:
                cand = _lookup_host_element_at_path(container, my_host_path)
                if cand is not None and cand.tag.lower() == "select":
                    host_sel_prev = cand
            children = process_select_element_children(
                raw_host, props, children, host_select_prev=host_sel_prev
            )
            strip_select_internal_props(props)
        elif tag_l == "textarea":
            host_ta_prev = None
            if path_enabled and container is not None and my_host_path is not None:
                cand = _lookup_host_element_at_path(container, my_host_path)
                if cand is not None and cand.tag.lower() == "textarea":
                    host_ta_prev = cand
            ta = process_textarea_element_children(
                raw_host, props, children, host_prev=host_ta_prev
            )
            children = ta.children
            textarea_controlled = ta.controlled
            textarea_host_default_value = ta.host_default_value
            strip_textarea_internal_props(props)

        rendered_children: list[RenderedNode] = []
        if isinstance(dsh, dict) and dsh.get("__html") is not None:
            if children:
                raise ValueError("Can only set one of `children` or `props.dangerouslySetInnerHTML`.")
            # Mirror React DOM: innerHTML is a property assignment, not a child node.
            props["innerHTML"] = format_dangerously_inner_html_value_dev(dsh.get("__html"))
            children = ()
        elif tag_l != "textarea" and children and not (isinstance(dsh, dict) and dsh.get("__html")):
            props.pop("innerHTML", None)
        child_slot = [0] if path_enabled else None
        child_prefix = my_host_path if path_enabled and my_host_path is not None else host_parent_path
        for c in _iter_visible_host_children(children):
            if is_dev():
                st = _dom_stack_str()
                if isinstance(c, (str, int, float)):
                    validate_text_nesting_dev(text=str(c), ancestor_info=info_inside, component_stack=st)
            rendered_children.extend(
                _render_to_virtual(
                    c,
                    portal_targets=portal_targets,
                    container=container,
                    parent_host_tag=node.type,
                    ancestor_info=info_inside,
                    host_parent_path=child_prefix,
                    next_child_index=child_slot,
                )
            )
        return [
            RenderedElement(
                tag=node.type,
                key=node.key,
                props=props,
                listeners=listeners,
                owner_stack=_dom_stack_str(),
                custom_on_property_mode=custom_on_property_mode,
                textarea_controlled=textarea_controlled,
                textarea_host_default_value=textarea_host_default_value,
                input_host_default_value=input_host_default_value,
                children=rendered_children,
            )
        ]

    # Wrapper/component types
    if isinstance(node.type, MemoType):
        return _render_to_virtual(
            create_element(node.type.inner, dict(node.props), ref=raw_element_ref(node)),
            portal_targets=portal_targets,
            container=container,
            parent_host_tag=parent_host_tag,
            ancestor_info=ancestor_info,
            host_parent_path=host_parent_path,
            next_child_index=next_child_index,
        )
    if isinstance(node.type, ForwardRefType):
        rendered = node.type.render(dict(node.props), raw_element_ref(node))
        return _render_to_virtual(
            rendered,
            portal_targets=portal_targets,
            container=container,
            parent_host_tag=parent_host_tag,
            ancestor_info=ancestor_info,
            host_parent_path=host_parent_path,
            next_child_index=next_child_index,
        )
    if callable(node.type):
        name = getattr(node.type, "__name__", "Anonymous")
        with _StackFrame(name):
            rendered = _render_component(node.type, dict(node.props), _get_component_hooks(node.type))
            return _render_to_virtual(
                rendered,
                portal_targets=portal_targets,
                container=container,
                parent_host_tag=parent_host_tag,
                ancestor_info=ancestor_info,
                host_parent_path=host_parent_path,
                next_child_index=next_child_index,
            )

    raise TypeError(f"Unsupported element type: {node.type!r}")


def _commit_children(
    *,
    container: Container,
    parent: ElementNode,
    next_children: list[RenderedNode],
    path: list[int],
    owner_stack: str = "",
) -> None:
    prev_children = list(parent.children)

    def make_node(v: RenderedNode) -> Node:
        if isinstance(v, RenderedText):
            return TextNode(text=v.text)
        el = ElementNode(tag=v.tag, key=v.key, props=dict(v.props))
        el._host_reconcile_id = allocate_host_reconcile_id()
        el._listeners = {k: list(vs) for k, vs in v.listeners.items()}
        el.custom_on_listener_property_modes = v.custom_on_property_mode
        if v.tag.lower() == "textarea":
            el._textarea_controlled = v.textarea_controlled
            el._textarea_host_default_value = v.textarea_host_default_value
        if v.tag.lower() == "input" and v.input_host_default_value is not None:
            el._input_host_default_value = v.input_host_default_value
        sync_host_style_from_props(el)
        return el

    def can_reuse(prev: Node, nxt: RenderedNode) -> bool:
        if isinstance(prev, TextNode) and isinstance(nxt, RenderedText):
            return True
        if isinstance(prev, ElementNode) and isinstance(nxt, RenderedElement):
            return prev.tag == nxt.tag and prev.key == nxt.key
        return False

    def apply_updates(node: Node, nxt: RenderedNode, p: list[int]) -> None:
        if isinstance(node, TextNode) and isinstance(nxt, RenderedText):
            if node.text != nxt.text:
                node.text = nxt.text
                _op(container, {"op": "text", "path": list(p), "value": nxt.text})
            return
        if isinstance(node, ElementNode) and isinstance(nxt, RenderedElement):
            if (
                nxt.tag.lower() == "textarea"
                and node._textarea_controlled
                and not nxt.textarea_controlled
            ):
                if is_dev():
                    warnings.warn(
                        "A component is changing a controlled textarea to be uncontrolled. "
                        "This is likely caused by the value changing from a defined to "
                        "undefined, which should not happen. Decide between using a controlled "
                        "or uncontrolled textarea element for the lifetime of the component. "
                        "More info: https://react.dev/link/controlled-components\n"
                        "    in textarea",
                        UserWarning,
                        stacklevel=2,
                    )
                prev_text = node.dom_textarea_value()
                nxt = replace(
                    nxt,
                    textarea_controlled=False,
                    children=[RenderedText(text=prev_text)] if prev_text else [],
                )
            if (
                is_dev()
                and nxt.tag.lower() == "input"
                and _input_had_change_listener(node)
                and "change" not in nxt.listeners
                and (_input_had_value_controlled(node) or _input_had_checked_controlled(node))
            ):
                warnings.warn(
                    "A component is changing a controlled input to be uncontrolled. "
                    "This is likely caused by the value changing from a defined to "
                    "undefined, which should not happen. Decide between using a controlled "
                    "or uncontrolled input element for the lifetime of the component. "
                    "More info: https://react.dev/link/controlled-components\n"
                    "    in input",
                    UserWarning,
                    stacklevel=2,
                )
            if (
                nxt.tag.lower() == "input"
                and _input_is_checkbox_or_radio(tag_l=nxt.tag.lower(), props=nxt.props)
                and "checked" in node.props
                and "checked" not in nxt.props
                and _input_had_change_listener(node)
            ):
                if is_dev():
                    warnings.warn(
                        "A component is changing a controlled input to be uncontrolled. "
                        "This is likely caused by the value changing from a defined to "
                        "undefined, which should not happen. Decide between using a controlled "
                        "or uncontrolled input element for the lifetime of the component. "
                        "More info: https://react.dev/link/controlled-components\n"
                        "    in input",
                        UserWarning,
                        stacklevel=2,
                    )
                nxt = replace(nxt, props={**nxt.props, "checked": node.props["checked"]})
            if (
                nxt.tag.lower() == "input"
                and "value" in node.props
                and "value" not in nxt.props
                and "change" in node._listeners
            ):
                # Upstream: DOMPropertyOperations "should not remove attributes for special
                # properties" — when an input was controlled, clearing `value` does not clear the
                # value attribute; React also warns in DEV in this situation.
                if is_dev():
                    warnings.warn(
                        "A component is changing a controlled input to be uncontrolled. "
                        "This is likely caused by the value changing from a defined to "
                        "undefined, which should not happen. Decide between using a controlled "
                        "or uncontrolled input element for the lifetime of the component. "
                        "More info: https://react.dev/link/controlled-components\n"
                        "    in input",
                        UserWarning,
                        stacklevel=2,
                    )
                nxt = replace(nxt, props={**nxt.props, "value": node.props["value"]})
            if (
                is_dev()
                and nxt.tag.lower() == "input"
                and "change" in nxt.listeners
                and not _input_had_change_listener(node)
                and (
                    (
                        "value" in nxt.props
                        and "value" not in node.props
                    )
                    or (
                        _input_is_checkbox_or_radio(tag_l=nxt.tag.lower(), props=nxt.props)
                        and "checked" in nxt.props
                        and (
                            "checked" not in node.props
                            or node.props.get("checked") is None
                        )
                    )
                )
            ):
                warnings.warn(
                    "A component is changing an uncontrolled input to be controlled. "
                    "This is likely caused by the value changing from undefined to "
                    "a defined value, which should not happen. Decide between using a "
                    "controlled or uncontrolled input element for the lifetime of the "
                    "component. More info: https://react.dev/link/controlled-components\n"
                    "    in input",
                    UserWarning,
                    stacklevel=2,
                )
            if nxt.tag.lower() == "textarea":
                node._textarea_controlled = nxt.textarea_controlled
                node._textarea_host_default_value = nxt.textarea_host_default_value
            if nxt.tag.lower() == "input" and nxt.input_host_default_value is not None:
                node._input_host_default_value = nxt.input_host_default_value
            # props diff
            changed: dict[str, Any] = {}
            removed: list[str] = []
            for k, v in nxt.props.items():
                if _host_update_prop_unchanged(node, k, v):
                    continue
                if (
                    nxt.tag.lower() == "input"
                    and k in ("defaultValue", "default_value")
                    and input_host_default_from_raw({k: v}) == node._input_host_default_value
                ):
                    continue
                changed[k] = v
            for k in list(node.props.keys()):
                if k not in nxt.props:
                    removed.append(k)
            if changed or removed:
                removed_payload: dict[str, Any] = {}
                for k in removed:
                    if _is_custom_element_dom_tag(node.tag) and k in node._custom_property_removed_values:
                        v_rem = node._custom_property_removed_values[k]
                        node.props[k] = v_rem
                        removed_payload[k] = v_rem
                    else:
                        del node.props[k]
                        removed_payload[k] = None
                node.props.update(changed)
                _op(
                    container,
                    {
                        "op": "updateProps",
                        "path": list(p),
                        "props": {**changed, **removed_payload},
                    },
                )
            dsh_nxt = nxt.props.get("dangerouslySetInnerHTML") or nxt.props.get("dangerously_set_inner_html")
            if (isinstance(dsh_nxt, dict) and dsh_nxt.get("__html") is not None) or nxt.children:
                node._inner_html_preserved = None
            sync_host_style_from_props(node)
            node._listeners = {k: list(vs) for k, vs in nxt.listeners.items()}
            node.custom_on_listener_property_modes = nxt.custom_on_property_mode
            _commit_children(
                container=container,
                parent=node,
                next_children=nxt.children,
                path=list(p) + [0],
                owner_stack=nxt.owner_stack,
            )
            return
        raise TypeError("commit apply_updates: incompatible node types")

    # Determine keyed reconciliation.
    keyed = any(isinstance(c, RenderedElement) and c.key is not None for c in next_children)
    if keyed:
        # Warn for duplicated keys (React-ish), including component stack info when available.
        seen: set[str] = set()
        dups: set[str] = set()
        for c in next_children:
            if isinstance(c, RenderedElement) and c.key is not None:
                if c.key in seen:
                    dups.add(c.key)
                else:
                    seen.add(c.key)
        if dups:
            from ryact_testkit.warnings import emit_warning

            keys = ", ".join(sorted(dups))
            msg = f"Encountered two children with the same key: {keys}"
            if owner_stack:
                msg = msg + "\n\n" + owner_stack
            emit_warning(msg, category=RuntimeWarning, stacklevel=3)

        prev_by_key: dict[str, Node] = {}
        prev_indices: dict[str, int] = {}
        for i, c2 in enumerate(prev_children):
            if isinstance(c2, ElementNode):
                k = c2.key
                if k is not None and k not in prev_by_key:
                    prev_by_key[k] = c2
                    prev_indices[k] = i

        next_nodes: list[Node] = []
        replaced_prev_indices: set[int] = set()
        replaced_keys: set[str] = set()
        for new_i, v in enumerate(next_children):
            if isinstance(v, RenderedElement) and v.key is not None and v.key in prev_by_key:
                prev = prev_by_key[v.key]
                if can_reuse(prev, v):
                    next_nodes.append(prev)
                else:
                    # Same key but incompatible node (e.g. tag/constructor changed) -> replace.
                    old_i = prev_indices.get(v.key)
                    if old_i is not None:
                        replaced_prev_indices.add(old_i)
                        replaced_keys.add(v.key)
                    n = make_node(v)
                    next_nodes.append(n)
                    _op(
                        container,
                        {
                            "op": "insert",
                            "path": list(path) + [new_i],
                            "tag": getattr(n, "tag", "#text"),
                            "key": getattr(v, "key", None),
                        },
                    )
            else:
                n = make_node(v)
                next_nodes.append(n)
                _op(
                    container,
                    {
                        "op": "insert",
                        "path": list(path) + [new_i],
                        "tag": getattr(n, "tag", "#text"),
                        "key": getattr(v, "key", None) if isinstance(v, RenderedElement) else None,
                    },
                )

        # Deletes: anything prev keyed not present in next keys.
        next_keys = {v.key for v in next_children if isinstance(v, RenderedElement) and v.key is not None}
        for old_i, c3 in enumerate(prev_children):
            if isinstance(c3, ElementNode):
                k = c3.key
                if (k is not None and k not in next_keys) or old_i in replaced_prev_indices:
                    _op(container, {"op": "delete", "path": list(path) + [old_i], "key": k})

        # Moves: compare prev index to new index for reused keyed nodes.
        for new_i, v in enumerate(next_children):
            if isinstance(v, RenderedElement) and v.key is not None and v.key in prev_indices:
                if v.key in replaced_keys:
                    continue
                old_i = prev_indices[v.key]
                if old_i != new_i:
                    _op(
                        container,
                        {
                            "op": "move",
                            "path": list(path),
                            "from": old_i,
                            "to": new_i,
                            "key": v.key,
                        },
                    )

        parent.children = next_nodes
        for i, (n, v) in enumerate(zip(parent.children, next_children, strict=True)):
            n.parent = parent
            apply_updates(n, v, list(path) + [i])
        return

    # Unkeyed: minimal index-based reconciliation.
    next_nodes2: list[Node] = []
    min_len = min(len(prev_children), len(next_children))
    for i in range(min_len):
        prev = prev_children[i]
        nxt = next_children[i]
        if can_reuse(prev, nxt):
            next_nodes2.append(prev)
        else:
            n = make_node(nxt)
            next_nodes2.append(n)
            _op(
                container,
                {
                    "op": "insert",
                    "path": list(path) + [i],
                    "tag": getattr(n, "tag", "#text"),
                    "key": None,
                },
            )

    # Inserts
    for i in range(min_len, len(next_children)):
        nxt = next_children[i]
        n = make_node(nxt)
        next_nodes2.append(n)
        _op(
            container,
            {
                "op": "insert",
                "path": list(path) + [i],
                "tag": getattr(n, "tag", "#text"),
                "key": None,
            },
        )

    # Deletes
    for i in range(len(next_children), len(prev_children)):
        _op(container, {"op": "delete", "path": list(path) + [i]})

    parent.children = next_nodes2
    for i, (n, v) in enumerate(zip(parent.children, next_children, strict=True)):
        n.parent = parent
        apply_updates(n, v, list(path) + [i])


def _host_path_to_node(container: Container, target: ElementNode) -> list[int]:
    rev: list[int] = []
    cur: Node | None = target
    while cur is not None and cur is not container.root:
        p = cur.parent
        if not isinstance(p, ElementNode):
            break
        try:
            idx = p.children.index(cur)
        except ValueError:
            break
        rev.append(idx)
        cur = p
    if cur is not container.root:
        raise ValueError("host_parent is not a descendant of container.root")
    rev.reverse()
    return rev


def render_into(
    container: Container,
    host_parent: ElementNode,
    element: Renderable,
) -> None:
    """Commit a nested tree as direct children of ``host_parent`` (legacy nested-root bridge)."""

    path = _host_path_to_node(container, host_parent)
    portal_acc: list[Any] = []
    next_v = _render_to_virtual(
        element,
        portal_targets=portal_acc,
        container=container,
        parent_host_tag=host_parent.tag,
        host_parent_path=tuple(path),
        next_child_index=[0],
    )
    _commit_children(
        container=container,
        parent=host_parent,
        next_children=next_v,
        path=path,
        owner_stack="",
    )


def _render_element(node: Renderable, *, portal_targets: list[Any]) -> list[Any]:
    if node is None:
        return []
    if isinstance(node, (str, int, float)):
        return [TextNode(text=str(node))]
    if isinstance(node, Element):
        # Host element is a string tag for now.
        if isinstance(node.type, str):
            if node.type == Fragment:
                out: list[Any] = []
                children = node.props.get("children", ())
                for c in children:
                    out.extend(_render_element(c, portal_targets=portal_targets))
                return out
            if node.type == Portal:
                target = node.props.get("container")
                if target is not None:
                    if target not in portal_targets:
                        portal_targets.append(target)
                    assert hasattr(target, "root")
                    target.root.children.clear()
                    children = node.props.get("children", ())
                    for c in children:
                        for rendered in _render_element(c, portal_targets=portal_targets):
                            target.root.append_child(rendered)
                return []
            validate_host_intrinsic_tag_name(node.type)
            el = ElementNode(
                tag=node.type,
                key=node.key,
                props=_host_props_normalized(node.props, node.type),
            )
            for prop, value in list(el.props.items()):
                if is_event_listener_prop(prop, value):
                    event_type = dom_event_type_for_listener_key(prop)
                    assert event_type is not None
                    el.add_event_listener(event_type, value)
                    del el.props[prop]
            children = node.props.get("children", ())
            for c in children:
                for rendered in _render_element(c, portal_targets=portal_targets):
                    el.append_child(rendered)
            return [el]
        if isinstance(node.type, MemoType):
            # DOM renderer is currently clear+rebuild; treat memo as a transparent wrapper.
            return _render_element(
                create_element(node.type.inner, dict(node.props), ref=raw_element_ref(node)),
                portal_targets=portal_targets,
            )
        if isinstance(node.type, ForwardRefType):
            rendered = node.type.render(
                dict(props_for_component_render(node.type, node.props)),
                raw_element_ref(node),
            )
            return _render_element(rendered, portal_targets=portal_targets)
        # Function or class component (see ryact.Component).
        if callable(node.type):
            rendered = _render_component(
                node.type,
                dict(props_for_component_render(node.type, node.props)),
                _get_component_hooks(node.type),
            )
            return _render_element(rendered, portal_targets=portal_targets)
    raise TypeError(f"Unsupported node type: {type(node)!r}")


_hooks_by_component = {}  # type: dict[int, list[Any]]


def _get_component_hooks(component: Any) -> list[Any]:
    # Very early identity model: key by function object identity.
    cid = id(component)
    if cid not in _hooks_by_component:
        _hooks_by_component[cid] = []
    return _hooks_by_component[cid]


@dataclass
class Root:
    container: Container
    _reconciler_root: Any
    _portal_targets: list[Any] | None = None
    _hydrating: bool = False
    _on_recoverable_error: Callable[[Exception], None] | None = None
    _unmounted: bool = False

    def unmount(self) -> None:
        if self._unmounted:
            raise RuntimeError("Cannot unmount a root that has already been unmounted.")
        self._unmounted = True
        rr = self._reconciler_root
        rr.pending_updates.clear()
        for host in list(self._portal_targets or []):
            if hasattr(host, "root"):
                for ch in list(host.root.children):
                    _detach_host_subtree(ch)
                host.root.children.clear()
        self._portal_targets = None
        for ch in list(self.container.root.children):
            _detach_host_subtree(ch)
        self.container.root.children.clear()
        self.container.ops.clear()

    def render(self, element: Element | None, *, lane: Lane = DEFAULT_LANE) -> None:
        if self._unmounted:
            raise RuntimeError("Cannot update an unmounted root.")

        def commit(payload: Any) -> None:
            if self._hydrating:
                # Minimal hydration slice: compare existing host tree with next payload and
                # report a recoverable mismatch, then replace.
                try:
                    _detect_hydration_mismatch(self.container, payload)
                except Exception as err:
                    if self._on_recoverable_error is not None:
                        self._on_recoverable_error(err)
            # Phase 24: incremental commit into existing host tree (primary root + portal targets).
            self.container.ops.clear()
            prev_portals = list(self._portal_targets or [])
            portal_targets: list[Any] = []
            next_v = _render_to_virtual(
                payload,
                portal_targets=portal_targets,
                container=self.container,
                parent_host_tag=None,
                host_parent_path=(),
                next_child_index=[0],
            )
            new_ids = {id(x) for x in portal_targets}
            for host in prev_portals:
                if id(host) not in new_ids and hasattr(host, "root"):
                    host.root.children.clear()
            _commit_children(
                container=self.container,
                parent=self.container.root,
                next_children=next_v,
                path=[],
                owner_stack="",
            )
            self._portal_targets = portal_targets

        rr = self._reconciler_root
        bind_commit(rr, commit)
        schedule_update_on_root(rr, Update(lane=lane, payload=element))
        if rr.scheduler is None:
            perform_work(rr, commit)


def create_root(container: Container, scheduler: Optional[Scheduler] = None) -> Root:
    return Root(
        container=container,
        _reconciler_root=create_reconciler_root(container, scheduler=scheduler),
    )


def hydrate_root(
    container: Container,
    element: Element | None,
    *,
    scheduler: Optional[Scheduler] = None,
    on_recoverable_error: Callable[[Exception], None] | None = None,
) -> Root:
    root = create_root(container, scheduler=scheduler)
    root._hydrating = True
    root._on_recoverable_error = on_recoverable_error
    root.render(element)
    return root


def _detect_hydration_mismatch(container: Container, payload: Any) -> None:
    # Very small mismatch detector: compare first host child tag + first text.
    existing = container.root.children[0] if container.root.children else None
    rendered = _render_element(payload, portal_targets=[])
    next0 = rendered[0] if rendered else None

    if isinstance(existing, ElementNode) and isinstance(next0, ElementNode):
        if existing.tag != next0.tag:
            raise ValueError(f"Hydration mismatch: tag {existing.tag!r} != {next0.tag!r}")
        # Compare first text child if both have one.
        ex_text = existing.children[0] if existing.children else None
        nx_text = next0.children[0] if next0.children else None
        if isinstance(ex_text, TextNode) and isinstance(nx_text, TextNode) and ex_text.text != nx_text.text:
            raise ValueError(f"Hydration mismatch: text {ex_text.text!r} != {nx_text.text!r}")
    elif existing is not None or next0 is not None:
        raise ValueError("Hydration mismatch: existing and next trees differ")
