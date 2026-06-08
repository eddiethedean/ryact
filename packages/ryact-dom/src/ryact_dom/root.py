from __future__ import annotations

import warnings
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field, replace
from typing import Any, Optional, Union, cast

from ryact.concurrent import Fragment, Offscreen, Portal, StrictMode, SuspenseList
from ryact.dev import is_dev
from ryact.element import UNDEFINED, Element, create_element, props_for_component_render, raw_element_ref
from ryact.hooks import FormStatusSnapshot, _render_component, form_status_provider
from ryact.reconciler import (
    _NESTED_UPDATE_LIMIT,
    DEFAULT_LANE,
    SYNC_LANE,
    Lane,
    Update,
    _apply_queued_class_state_for_sync_render,
    _call_legacy_will_receive_props,
    _call_legacy_will_update,
    _peek_merged_class_state_dict,
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
from .event_listener import ensure_selectionchange_subscription
from .host_focus import (
    autofocus_host_if_needed,
    preserve_focus_before_commit,
    restore_preserved_focus_in_container,
)
from .host_style import sync_host_style_from_props
from .html_props import (
    _dom_prop_lookup_key,
    _is_custom_element_dom_tag,
    _merge_class_values,
    dom_event_type_for_listener_key,
    is_event_listener_prop,
    normalize_host_prop_dict,
    parse_event_listener_prop,
    warn_intrinsic_html_tag_casing_dev,
)
from .input_binding import (
    input_host_default_from_raw,
    preserve_null_defaultvalue_inplace,
    preserve_value_on_invalid_form_field_inplace,
)
from .input_host import init_input_host_on_mount, sync_input_host_after_props_update
from .intrinsic_tag_dev import (
    format_dangerously_inner_html_value_dev,
    warn_unrecognized_host_tag_dev,
)
from .legacy_mount import register_modern_root, warn_replacing_react_children_with_new_root
from .mount_validation import prepare_host_mount_props, void_element_children_or_innerhtml_error
from .option_host import (
    flatten_option_label_in_order,
    init_option_host_on_mount,
    process_option_children_after_render,
    strip_option_internal_props,
    sync_option_host_after_props_update,
)
from .root_dev import (
    register_root_for_container,
    unregister_root_for_container,
    warn_create_root_jsx_element,
    warn_create_root_on_document_body,
    warn_hydrate_root_missing_children,
    warn_render_extra_argument,
    warn_render_extra_callback,
    warn_render_invalid_child,
    warn_unmount_extra_callback,
)
from .select_binding import process_select_element_children, strip_select_internal_props
from .svg_namespace import namespace_for_host_child
from .tag_sanitization import validate_host_intrinsic_tag_name
from .textarea_binding import process_textarea_element_children, strip_textarea_internal_props
from .use_id_host import make_use_id_allocator
from .validate_dom_nesting import (
    AncestorInfoDev,
    initial_ancestor_info_dev,
    updated_ancestor_info_dev,
    validate_dom_nesting_host_child_dev,
    validate_text_nesting_dev,
)

Renderable = Union[Element, str, int, float, None]


def _reset_namespace_context_stack(container: Container | None) -> None:
    if container is not None:
        container._ryact_namespace_context_stack = []  # type: ignore[attr-defined]


def _peek_namespace_context(container: Container | None) -> tuple[str | None, str | None]:
    if container is None:
        return (None, None)
    stack = getattr(container, "_ryact_namespace_context_stack", None)
    if isinstance(stack, list) and stack:
        ns, tag = stack[-1]
        return (ns, tag)
    return (None, None)


def _push_namespace_context(container: Container, namespace: str, tag: str) -> None:
    stack = list(getattr(container, "_ryact_namespace_context_stack", []))
    stack.append((namespace, tag))
    container._ryact_namespace_context_stack = stack  # type: ignore[attr-defined]


def _pop_namespace_context(container: Container) -> None:
    stack = list(getattr(container, "_ryact_namespace_context_stack", []))
    if stack:
        stack.pop()
    container._ryact_namespace_context_stack = stack  # type: ignore[attr-defined]


def _set_portal_namespace_inheritance(
    *,
    portal_target: Container,
    main_container: Container,
    host_parent_path: tuple[int, ...],
) -> None:
    parent_ns, parent_tag = _peek_namespace_context(main_container)
    if parent_ns is None and host_parent_path:
        bubble_host = _lookup_host_element_at_path(main_container, host_parent_path)
        if bubble_host is not None:
            parent_ns = bubble_host._namespace_uri
            parent_tag = bubble_host.tag
    portal_target._ryact_portal_parent_namespace = parent_ns  # type: ignore[attr-defined]
    portal_target._ryact_portal_parent_tag = parent_tag  # type: ignore[attr-defined]


def _iter_visible_host_children(children: object, *, owner_stack: str = "") -> list[object]:
    """Expand host ``children`` like React (skip null/false; flatten arrays; accept iterables)."""

    from .children_expansion import expand_host_children

    return expand_host_children(children, owner_stack=owner_stack)


def _host_props_normalized(props: Mapping[str, Any], tag: str) -> dict[str, Any]:
    prepared = prepare_host_mount_props(props, tag=tag)
    norm = normalize_host_prop_dict(prepared, tag=tag)
    from .form_actions import RYACT_ACTION_FN_KEY, RYACT_FORM_ACTION_FN_KEY
    from .form_data import coerce_form_action_value

    tl = tag.lower()
    if tl == "form":
        fn = coerce_form_action_value(prepared.get("action"))
        if callable(fn):
            norm[RYACT_ACTION_FN_KEY] = fn
    if tl in ("button", "input"):
        raw = prepared.get("formAction")
        if raw is None:
            raw = prepared.get("formaction")
        fn = coerce_form_action_value(raw)
        if callable(fn):
            norm[RYACT_FORM_ACTION_FN_KEY] = fn
    return norm


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
_root_render_depth: int = 0


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


_LEGACY_CONTEXT_LINK = "https://react.dev/link/legacy-context"
_WARNING_KEYS_LINK = "https://react.dev/link/warning-keys"


def _dom_legacy_stack(container: Container | None) -> list[dict[str, Any]]:
    if container is None:
        return [{}]
    stack = getattr(container, "_ryact_dom_legacy_stack", None)
    if not isinstance(stack, list) or not stack:
        stack = [{}]
        container._ryact_dom_legacy_stack = stack  # type: ignore[attr-defined]
    return stack


def _dom_legacy_merged(container: Container | None) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for layer in _dom_legacy_stack(container):
        merged.update(layer)
    return merged


def _dom_class_parent_owner_token(
    *,
    container: Container | None,
    host_parent_path: tuple[int, ...],
) -> tuple[Any, ...]:
    from ryact import hooks as _hooks_mod

    parent_class = _hooks_mod._current_class_component_instance
    if parent_class is not None:
        return ("class", id(parent_class))
    if container is not None:
        fn_stack = getattr(container, "_ryact_fn_render_stack", None)
        if isinstance(fn_stack, list) and fn_stack:
            return ("fn", fn_stack[-1])
    return ("host", host_parent_path)


def _dom_class_instance_cache_key(
    node_type: Any,
    element_key: str | None,
    parent_token: tuple[Any, ...],
    comp_slot: int | None,
) -> tuple[Any, ...]:
    if element_key is not None:
        return (node_type, element_key)
    return (node_type, None, parent_token, comp_slot if comp_slot is not None else 0)


def _dom_has_legacy_context_types(cls: type[Any]) -> bool:
    cts = getattr(cls, "contextTypes", None)
    return isinstance(cts, dict) and bool(cts)


def _dom_cwrp_context(inst: Any, *, has_legacy_ctx: bool, next_ctx: Any) -> Any:
    if has_legacy_ctx:
        return next_ctx
    stable = getattr(inst, "_ryact_dom_cwrp_empty_ctx", None)
    if stable is None:
        stable = {}
        inst._ryact_dom_cwrp_empty_ctx = stable  # type: ignore[attr-defined]
    return stable


def _dom_push_legacy_child_context(container: Container | None, inst: Any, cls: type[Any]) -> None:
    layer: dict[str, Any] = {}
    get_child = getattr(cls, "getChildContext", None)
    child_cts = getattr(cls, "childContextTypes", None)
    if child_cts is not None and callable(get_child):
        try:
            extra = get_child(inst)
            if isinstance(extra, dict):
                layer = extra
        except Exception:
            layer = {}
    _dom_legacy_stack(container).append(layer)


def _dom_pop_legacy_child_context(container: Container | None) -> None:
    stack = _dom_legacy_stack(container)
    if len(stack) > 1:
        stack.pop()


def _dom_apply_class_instance_context(inst: Any, cls: type[Any], container: Container | None) -> None:
    from ryact.context import Context

    merged = _dom_legacy_merged(container)
    ct = getattr(cls, "contextType", None)
    cts = getattr(cls, "contextTypes", None)
    if isinstance(ct, Context):
        inst._context = ct._get()  # type: ignore[attr-defined]
    elif isinstance(cts, dict) and cts:
        new_ctx = {k: merged.get(k) for k in cts}
        prev = getattr(inst, "_context", None)
        if isinstance(prev, dict) and prev == new_ctx:
            inst._context = prev  # type: ignore[attr-defined]
        else:
            inst._context = new_ctx  # type: ignore[attr-defined]
    else:
        inst._context = None  # type: ignore[attr-defined]


def _dom_peek_legacy_context(cls: type[Any], container: Container | None) -> Any:
    from ryact.context import Context

    merged = _dom_legacy_merged(container)
    ct = getattr(cls, "contextType", None)
    cts = getattr(cls, "contextTypes", None)
    if isinstance(ct, Context):
        return ct._get()
    if isinstance(cts, dict) and cts:
        return {k: merged.get(k) for k in cts}
    return None


def _dom_warn_class_legacy_context_dev(cls: type[Any], name: str) -> None:
    if not is_dev():
        return
    child_cts = getattr(cls, "childContextTypes", None)
    get_child = getattr(cls, "getChildContext", None)
    cts = getattr(cls, "contextTypes", None)
    stack = _dom_stack_str()
    if child_cts is not None and callable(get_child):
        msg = (
            f"{name} uses the legacy childContextTypes API which will soon be removed. "
            f"Use create_context() instead. ({_LEGACY_CONTEXT_LINK})"
        )
        if stack:
            msg = msg + "\n" + stack
        warnings.warn(msg, RuntimeWarning, stacklevel=4)
    if isinstance(cts, dict) and cts:
        msg = (
            f"{name} uses the legacy contextTypes API which will soon be removed. "
            f"Use create_context() with static contextType instead. ({_LEGACY_CONTEXT_LINK})"
        )
        if stack:
            msg = msg + "\n" + stack
        warnings.warn(msg, RuntimeWarning, stacklevel=4)


def _dom_warn_function_component_dev(fn: Any, name: str) -> None:
    if not is_dev():
        return
    stack = _dom_stack_str()
    if getattr(fn, "getDerivedStateFromProps", None) is not None:
        msg = f"{name}: Function components do not support getDerivedStateFromProps."
        if stack:
            msg = msg + "\n" + stack
        warnings.warn(msg, RuntimeWarning, stacklevel=4)
    if getattr(fn, "childContextTypes", None) is not None:
        msg = f"childContextTypes cannot be defined on a function component.\n  {name}.childContextTypes = ...\n"
        if stack:
            msg = msg + "\n" + stack
        warnings.warn(msg, RuntimeWarning, stacklevel=4)
    cts_fn = getattr(fn, "contextTypes", None)
    if isinstance(cts_fn, dict) and cts_fn:
        msg = (
            f"{name} uses the legacy contextTypes API which will be removed soon. "
            f"Use create_context() with React.useContext() instead. ({_LEGACY_CONTEXT_LINK})"
        )
        if stack:
            msg = msg + "\n" + stack
        warnings.warn(msg, RuntimeWarning, stacklevel=4)


def _dom_legacy_context_for_hooks(container: Container | None, fn: Any) -> dict[str, Any] | None:
    cts = getattr(fn, "contextTypes", None)
    if not isinstance(cts, dict) or not cts:
        return None
    merged = _dom_legacy_merged(container)
    return {k: merged.get(k) for k in cts}


def _dom_warn_missing_keys_on_component_return(component_name: str, rendered: Any) -> None:
    from ryact.concurrent import Fragment
    from ryact.element import Element

    children: tuple[Any, ...] | list[Any] | None = None
    if isinstance(rendered, Element) and rendered.type == Fragment:
        raw = rendered.props.get("children", ())
        children = raw if isinstance(raw, (list, tuple)) else (raw,)
    elif isinstance(rendered, (list, tuple)):
        children = rendered
    if children is None:
        return
    element_children = [c for c in children if isinstance(c, Element)]
    if len(element_children) < 2 or not any(c.key is None for c in element_children):
        return
    stack = _dom_stack_str()
    msg = (
        'Each child in a list should have a unique "key" prop.\n\n'
        f"Check the render method of `{component_name}`. "
        f"See {_WARNING_KEYS_LINK} for more information."
    )
    if stack:
        msg = msg + "\n" + stack
    warnings.warn(msg, RuntimeWarning, stacklevel=4)


def _dom_effect_lists(container: Container | None) -> tuple[list[Any], list[Any]]:
    if container is None:
        return [], []
    layout = getattr(container, "_ryact_dom_layout_effects", None)
    passive = getattr(container, "_ryact_dom_passive_effects", None)
    if not isinstance(layout, list):
        layout = []
        container._ryact_dom_layout_effects = layout  # type: ignore[attr-defined]
    if not isinstance(passive, list):
        passive = []
        container._ryact_dom_passive_effects = passive  # type: ignore[attr-defined]
    return layout, passive


def _reset_dom_effect_lists(container: Container) -> tuple[list[Any], list[Any]]:
    layout: list[Any] = []
    passive: list[Any] = []
    container._ryact_dom_layout_effects = layout  # type: ignore[attr-defined]
    container._ryact_dom_passive_effects = passive  # type: ignore[attr-defined]
    return layout, passive


def _flush_dom_layout_effects(container: Container) -> None:
    from ryact.hooks import _set_commit_context

    from .error_reporting import run_effects_phased

    layout, _ = _dom_effect_lists(container)
    container._ryact_dom_layout_effects = []  # type: ignore[attr-defined]
    _set_commit_context(phase="layout", stack=None)
    try:
        run_effects_phased(layout, container=container)
    finally:
        _set_commit_context(phase=None, stack=None)


def _flush_dom_passive_effects(container: Container) -> None:
    from ryact.hooks import _set_commit_context, _set_dom_effect_boundary_stack

    from .error_reporting import run_effects_phased

    _, passive = _dom_effect_lists(container)
    container._ryact_dom_passive_effects = []  # type: ignore[attr-defined]
    try:
        _set_commit_context(phase="passive", stack=None)
        run_effects_phased(passive, container=container)
    finally:
        _set_commit_context(phase=None, stack=None)
        _set_dom_effect_boundary_stack([])


def _flush_dom_hook_effects(container: Container) -> None:
    _flush_dom_layout_effects(container)
    _flush_dom_passive_effects(container)


def _dom_render_function_component_output(
    *,
    rendered: Any,
    component_name: str,
    container: Container | None,
    portal_targets: list[Any],
    parent_host_tag: str | None,
    ancestor_info: AncestorInfoDev | None,
    host_parent_path: tuple[int, ...],
    next_child_index: list[int] | None,
    class_render_depth: int,
) -> list[RenderedNode]:
    from ryact.element import coerce_top_level_render_result

    from .children_expansion import expand_rendered_children

    owner_stack = _dom_stack_str() if is_dev() else ""
    rendered = expand_rendered_children(rendered, owner_stack=owner_stack)
    rendered = coerce_top_level_render_result(rendered)
    if is_dev():
        _dom_warn_missing_keys_on_component_return(component_name, rendered)
    return _render_to_virtual(
        rendered,
        portal_targets=portal_targets,
        container=container,
        parent_host_tag=parent_host_tag,
        ancestor_info=ancestor_info,
        host_parent_path=host_parent_path,
        next_child_index=next_child_index,
        class_render_depth=class_render_depth,
    )


def _op(container: Container, payload: dict[str, object]) -> None:
    container.ops.append(payload)


def _dom_function_schedule_update(container: Container | None) -> Callable[[Lane], None] | None:
    """Wire ``useState`` dispatch to the DOM root reconciler (function components)."""

    if container is None or container._ryact_dom_root is None:
        return None
    rr = container._ryact_dom_root._reconciler_root

    def schedule_update(lane: Lane) -> None:
        from ryact.hooks import _current_commit_phase, _render_depth
        from ryact.reconciler import _check_nested_update_depth

        schedule_update_on_root(rr, Update(lane=lane, payload=rr._last_element))
        if rr.scheduler is None and bool(getattr(container, "_ryact_dom_in_full_commit", False)):
            if bool(getattr(rr, "_is_batching_updates", False)):
                return
            if _render_depth > 0 and _current_commit_phase is None:
                try:
                    _check_nested_update_depth(rr)
                except RuntimeError as err:
                    if "Maximum update depth exceeded" in str(err):
                        from .error_reporting import report_uncaught_error

                        report_uncaught_error(container, err)
                        return
                    raise
                return
            if bool(getattr(container, "_ryact_dom_in_ref_attach", False)):
                if bool(getattr(container, "_ryact_dom_ref_attach_aborted", False)):
                    return
                ref_updates = int(getattr(container, "_ryact_dom_ref_attach_updates", 0) or 0) + 1
                container._ryact_dom_ref_attach_updates = ref_updates  # type: ignore[attr-defined]
                if ref_updates >= 50:
                    container._ryact_dom_ref_attach_aborted = True  # type: ignore[attr-defined]
                    from .error_reporting import report_uncaught_error

                    err = RuntimeError(
                        "Maximum update depth exceeded. This can happen when a component repeatedly "
                        "calls setState inside componentWillUpdate or componentDidUpdate. React limits "
                        "the number of nested updates to prevent infinite loops."
                    )
                    report_uncaught_error(container, err)
                    rr._nested_update_count = 0  # type: ignore[attr-defined]
                    return
                return
            try:
                _check_nested_update_depth(rr)
            except RuntimeError as err:
                if "Maximum update depth exceeded" in str(err):
                    from .error_reporting import report_uncaught_error

                    report_uncaught_error(container, err)
                    return
                raise
            commit = getattr(rr, "_commit_fn", None)
            if callable(commit):
                perform_work(rr, commit)

    return schedule_update


def _wire_dom_class_schedule_update(container: Container | None, instance: Any) -> None:
    """Class ``setState`` in the DOM virtual-tree renderer."""

    if container is None or container._ryact_dom_root is None:
        return
    rr = container._ryact_dom_root._reconciler_root

    def _schedule_for_setstate() -> None:
        from ryact.hooks import _render_depth

        container_for_inst = getattr(instance, "_ryact_dom_container", None)
        in_full_commit = bool(
            getattr(container_for_inst, "_ryact_dom_in_full_commit", False)
        ) if container_for_inst is not None else False

        if _render_depth == 0 and in_full_commit and (
            bool(getattr(instance, "_ryact_legacy_mount", False))
            or bool(getattr(instance, "_ryact_dom_in_did_catch", False))
        ):
            from ryact.reconciler import _apply_queued_class_state_for_sync_render

            _apply_queued_class_state_for_sync_render(instance, rr, strict=False)
            dirty = getattr(container, "_ryact_dom_mount_dirty", None)
            if not isinstance(dirty, list):
                dirty = []
                container._ryact_dom_mount_dirty = dirty  # type: ignore[attr-defined]
            if instance not in dirty:
                dirty.append(instance)
            return

        if _render_depth > 0:
            from ryact.hooks import _current_class_component_instance

            caller = _current_class_component_instance
            if caller is not instance:
                if bool(getattr(instance, "_ryact_dom_in_cwrp", False)):
                    from ryact.reconciler import _apply_queued_class_state_for_sync_render

                    _apply_queued_class_state_for_sync_render(instance, rr, strict=False)
                    return
                from ryact.reconciler import _apply_queued_class_state_for_sync_render

                _apply_queued_class_state_for_sync_render(instance, rr, strict=False)
                dirty = getattr(container, "_ryact_dom_mount_dirty", None)
                if not isinstance(dirty, list):
                    dirty = []
                    container._ryact_dom_mount_dirty = dirty  # type: ignore[attr-defined]
                if instance not in dirty:
                    dirty.append(instance)
                return
            if not getattr(instance, "_ryact_did_mount", False):
                return
            if bool(getattr(instance, "_ryact_dom_in_cwrp", False)):
                from ryact.reconciler import _apply_first_queued_class_state_for_sync_render

                _apply_first_queued_class_state_for_sync_render(instance, rr, strict=False)
                return
            cwrp_ran = getattr(container, "_ryact_dom_cwrp_ran", None)
            if isinstance(cwrp_ran, set) and instance in cwrp_ran:
                from ryact.reconciler import _apply_queued_class_state_for_sync_render

                _apply_queued_class_state_for_sync_render(instance, rr, strict=False)
                return
            if bool(getattr(instance, "_ryact_pending_mount", False)):
                from ryact.reconciler import _apply_first_queued_class_state_for_sync_render

                _apply_first_queued_class_state_for_sync_render(instance, rr, strict=False)
            if bool(getattr(instance, "_ryact_dom_suppress_dirty", False)):
                instance._ryact_dom_suppress_dirty = False  # type: ignore[attr-defined]
                from ryact.reconciler import _apply_queued_class_state_for_sync_render

                _apply_queued_class_state_for_sync_render(instance, rr, strict=False)
                return
            dirty = getattr(container, "_ryact_dom_mount_dirty", None)
            if not isinstance(dirty, list):
                dirty = []
                container._ryact_dom_mount_dirty = dirty  # type: ignore[attr-defined]
            if instance not in dirty:
                dirty.append(instance)
            return
        el = getattr(rr, "_last_element", None)
        if el is not None:
            from ryact.concurrent import current_update_lane

            lane = current_update_lane() or DEFAULT_LANE
            if bool(getattr(rr, "_force_sync_updates", False)) and int(lane.priority) > int(
                SYNC_LANE.priority
            ):
                lane = SYNC_LANE
            schedule_update_on_root(
                rr,
                Update(
                    lane=lane,
                    payload=el,
                    batched_with_force=bool(getattr(rr, "_force_sync_updates", False)),
                ),
            )
            if bool(getattr(rr, "_is_batching_updates", False)):
                return
            if bool(getattr(container, "_ryact_dom_in_mount_commit", False)):
                return
            from .event_listener import event_dispatch_in_progress

            if event_dispatch_in_progress():
                return
            if rr.scheduler is None:
                if bool(getattr(rr, "_force_sync_updates", False)):
                    return
                commit = getattr(rr, "_commit_fn", None)
                if callable(commit):
                    perform_work(rr, commit)

    instance._schedule_update = _schedule_for_setstate  # type: ignore[attr-defined]
    if container is not None:
        instance._ryact_dom_container = container  # type: ignore[attr-defined]
        from .legacy_mount import is_legacy_container

        instance._ryact_legacy_mount = is_legacy_container(container)  # type: ignore[attr-defined]


@dataclass(frozen=True)
class RenderedText:
    text: str


@dataclass(frozen=True, kw_only=True)
class RenderedElement:
    tag: str
    key: str | None
    ref: Any | None = None
    props: dict[str, Any]
    listeners: dict[str, list[Callable[[Any], None]]]
    listeners_capture: dict[str, list[Callable[[Any], None]]] = field(default_factory=dict)
    owner_stack: str
    component_owner_id: int | None = None
    error_boundary: Any | None = None
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


def _link_portal_event_bubble(portal_container: Container, bubble_parent: ElementNode) -> None:
    """Connect portal top-level hosts to the React parent for synthetic bubbling."""

    from .event_listener import link_event_parent

    for ch in portal_container.root.children:
        if isinstance(ch, ElementNode):
            link_event_parent(ch, bubble_parent)


def _rendered_tree_has_click_listener(nodes: list[RenderedNode]) -> bool:
    for n in nodes:
        if isinstance(n, RenderedElement):
            if n.listeners.get("click"):
                return True
            if _rendered_tree_has_click_listener(n.children):
                return True
    return False


def _detach_host_subtree(node: Node) -> None:
    if isinstance(node, ElementNode):
        from .dom_internals import (
            purge_class_instances_for_detached_subtree,
            purge_component_dom_registry_for_subtree,
        )
        from .host_refs import detach_host_ref

        container = getattr(node, "_event_container", None)
        dom_root = getattr(container, "_ryact_dom_root", None) if container is not None else None
        if dom_root is not None:
            purge_class_instances_for_detached_subtree(dom_root, node)
        detach_host_ref(node)
        purge_component_dom_registry_for_subtree(node)
        for ch in list(node.children):
            _detach_host_subtree(ch)
        node.children.clear()
    node.parent = None


def _is_dom_error_boundary(inst: Any) -> bool:
    return callable(getattr(inst, "componentDidCatch", None)) or callable(
        getattr(type(inst), "getDerivedStateFromError", None)
    )


def _dom_boundary_stack(container: Container | None) -> list[Any]:
    if container is None:
        return []
    stack = getattr(container, "_ryact_dom_boundary_stack", None)
    if not isinstance(stack, list):
        stack = []
        container._ryact_dom_boundary_stack = stack  # type: ignore[attr-defined]
    return stack


def _dom_boundary_stack(container: Container | None) -> list[Any]:
    if container is None:
        return []
    stack = getattr(container, "_ryact_dom_boundary_stack", None)
    if not isinstance(stack, list):
        stack = []
        container._ryact_dom_boundary_stack = stack  # type: ignore[attr-defined]
    return stack


def _dom_tag_class_error_boundary(container: Container | None, inst: Any) -> None:
    if container is None:
        return
    boundary = getattr(container, "_ryact_dom_current_boundary", None)
    if boundary is not None:
        inst._ryact_dom_error_boundary = boundary  # type: ignore[attr-defined]


def _dom_restore_boundary_captured_error(boundary: Any, captured: BaseException) -> None:
    state = getattr(boundary, "_state", None)
    if isinstance(state, dict):
        state["error"] = captured
    pending = getattr(boundary, "_pending_state_updates", None)
    if isinstance(pending, list):
        pending.clear()


def _dom_catch_on_boundary(
    container: Container,
    boundary: Any,
    err: BaseException,
    *,
    prefer_first_captured_error: bool = False,
) -> bool:
    from .error_reporting import log_boundary_component_error

    did_catch = getattr(boundary, "componentDidCatch", None)
    gdsfe = getattr(type(boundary), "getDerivedStateFromError", None)
    if not (callable(did_catch) or callable(gdsfe)):
        return False
    boundary_name = getattr(type(boundary), "__name__", "ErrorBoundary")
    deferred_log_err: BaseException | None = None
    try:
        log_boundary_component_error(container, err, boundary_name=boundary_name)
    except BaseException as log_err:
        deferred_log_err = log_err
    existing_err: BaseException | None = None
    boundary_state = getattr(boundary, "_state", None)
    if isinstance(boundary_state, dict):
        captured = boundary_state.get("error")
        if isinstance(captured, BaseException):
            existing_err = captured
    if callable(gdsfe) and existing_err is None:
        partial = gdsfe(err)
        if isinstance(partial, dict) and isinstance(getattr(boundary, "_state", None), dict):
            boundary._state.update(partial)  # type: ignore[attr-defined]
    if callable(did_catch):
        boundary._ryact_dom_in_did_catch = True  # type: ignore[attr-defined]
        try:
            did_catch(err)
        finally:
            boundary._ryact_dom_in_did_catch = False  # type: ignore[attr-defined]
        if existing_err is not None and prefer_first_captured_error:
            _dom_restore_boundary_captured_error(boundary, existing_err)
        if is_dev() and not callable(gdsfe):
            from .error_reporting import log_console_error_message

            log_console_error_message(
                container,
                f"{boundary_name}: Error boundaries should implement getDerivedStateFromError(). "
                "In that method, return a state update to display an error message or fallback UI.",
            )
    recovery = int(getattr(container, "_ryact_dom_error_recovery_count", 0) or 0) + 1
    container._ryact_dom_error_recovery_count = recovery  # type: ignore[attr-defined]
    if recovery > _NESTED_UPDATE_LIMIT:
        raise RuntimeError(
            "Maximum update depth exceeded. This can happen when a component repeatedly "
            "calls setState inside componentWillUpdate or componentDidUpdate. React limits "
            "the number of nested updates to prevent infinite loops."
        ) from None
    dom_root = container._ryact_dom_root
    rr = dom_root._reconciler_root if dom_root is not None else None
    if rr is not None:
        _apply_queued_class_state_for_sync_render(boundary, rr, strict=False)
    if existing_err is not None and prefer_first_captured_error:
        _dom_restore_boundary_captured_error(boundary, existing_err)
    container._ryact_dom_lifecycle_recommit = True  # type: ignore[attr-defined]
    if deferred_log_err is not None:
        deferred = getattr(container, "_ryact_dom_deferred_boundary_errors", None)
        if not isinstance(deferred, list):
            deferred = []
            container._ryact_dom_deferred_boundary_errors = deferred  # type: ignore[attr-defined]
        deferred.append(deferred_log_err)
    return True


def _dom_flush_deferred_boundary_errors(container: Container) -> None:
    deferred = getattr(container, "_ryact_dom_deferred_boundary_errors", None)
    if not isinstance(deferred, list) or not deferred:
        return
    container._ryact_dom_deferred_boundary_errors = []  # type: ignore[attr-defined]
    _dom_raise_collected_errors(deferred, label="error boundary logging errors")


def _dom_handle_lifecycle_error(
    container: Container | None,
    inst: Any,
    err: BaseException,
    *,
    prefer_first_captured_error: bool = False,
) -> bool:
    if container is None:
        return False
    boundary = getattr(inst, "_ryact_dom_error_boundary", None)
    if boundary is None:
        return False
    return _dom_catch_on_boundary(
        container,
        boundary,
        err,
        prefer_first_captured_error=prefer_first_captured_error,
    )


def _dom_resolve_effect_boundary(container: Container, fn: Any) -> Any | None:
    dom_root = getattr(container, "_ryact_dom_root", None)
    if dom_root is None:
        return None
    ids = getattr(fn, "_ryact_dom_boundary_ids", None)
    if isinstance(ids, list) and ids:
        by_id = {id(inst): inst for inst in dom_root._class_instances.values()}
        for bid in reversed(ids):
            inst = by_id.get(bid)
            if inst is not None and _is_dom_error_boundary(inst):
                return inst
    names = getattr(fn, "_ryact_dom_boundary_names", None)
    if isinstance(names, list) and names:
        target = names[-1]
        candidates = [
            inst
            for inst in dom_root._class_instances.values()
            if getattr(type(inst), "__name__", "") == target and _is_dom_error_boundary(inst)
        ]
        if candidates:
            return candidates[-1]
    return None


def _dom_catch_effect_error(container: Container, fn: Any, err: BaseException) -> bool:
    boundary = _dom_resolve_effect_boundary(container, fn)
    if boundary is None:
        return False
    if not _dom_catch_on_boundary(container, boundary, err, prefer_first_captured_error=False):
        return False
    dom_root = container._ryact_dom_root
    rr = dom_root._reconciler_root if dom_root is not None else None
    if rr is not None and rr.scheduler is None and not bool(getattr(rr, "_is_batching_updates", False)):
        commit = getattr(rr, "_commit_fn", None)
        if callable(commit):
            perform_work(rr, commit)
    return True


def _dom_report_or_reraise_uncaught(container: Container, err: BaseException) -> None:
    """createRoot logs uncaught commit errors; legacy roots still re-raise."""

    from .error_reporting import _is_legacy_container, report_uncaught_error

    report_uncaught_error(container, err)
    if _is_legacy_container(container) or (
        isinstance(err, RuntimeError) and "Maximum update depth exceeded" in str(err)
    ):
        raise err


def _dom_raise_collected_errors(errors: list[BaseException], *, label: str) -> None:
    if not errors:
        return
    if len(errors) == 1:
        raise errors[0]
    try:
        raise ExceptionGroup(label, errors)  # type: ignore[misc]
    except (NameError, TypeError):
        agg = RuntimeError(label)
        agg.errors = errors  # type: ignore[attr-defined]
        raise agg from errors[0]


def _run_dom_class_gsbu_before_commit(root: Root) -> None:
    """Run getSnapshotBeforeUpdate for pending class updates (deepest first)."""

    container = root.container
    cdu_order = getattr(container, "_ryact_dom_cdu_order", None)
    if not isinstance(cdu_order, list) or not cdu_order:
        return
    cdu_depth = getattr(container, "_ryact_dom_cdu_depth", None)
    if isinstance(cdu_depth, dict):
        work = sorted(cdu_order, key=lambda inst: cdu_depth.get(inst, 0), reverse=True)
    else:
        work = list(reversed(cdu_order))
    errors: list[BaseException] = []
    for inst in work:
        if not getattr(inst, "_ryact_dom_pending_cdu", False):
            continue
        gsbu = getattr(inst, "getSnapshotBeforeUpdate", None)
        if not callable(gsbu):
            continue
        prev = getattr(inst, "_ryact_dom_cdu_prev", None)
        if not isinstance(prev, tuple) or len(prev) != 2:
            continue
        prev_props, prev_state = prev
        try:
            snap = gsbu(prev_props, prev_state)
            inst._ryact_dom_gsbu_snapshot = snap  # type: ignore[attr-defined]
        except BaseException as err:
            errors.append(err)
    _dom_raise_collected_errors(errors, label="getSnapshotBeforeUpdate errors")


def _dom_render_class_output(
    *,
    container: Container | None,
    inst: Any,
    rendered: Any,
    portal_targets: list[Any],
    parent_host_tag: str | None,
    ancestor_info: AncestorInfoDev | None,
    host_parent_path: tuple[int, ...],
    next_child_index: list[int] | None,
    class_render_depth: int = 0,
) -> list[RenderedNode]:
    stack = _dom_boundary_stack(container)
    is_boundary = _is_dom_error_boundary(inst)
    prev_current_boundary = getattr(container, "_ryact_dom_current_boundary", None) if container is not None else None
    if is_boundary and container is not None:
        container._ryact_dom_current_boundary = inst  # type: ignore[attr-defined]
    if is_boundary:
        stack.append(inst)
    from ryact.element import coerce_top_level_render_result

    from .children_expansion import expand_rendered_children

    owner_stack = _dom_stack_str() if is_dev() else ""
    rendered = expand_rendered_children(rendered, owner_stack=owner_stack)
    rendered = coerce_top_level_render_result(rendered)
    cls = type(inst)
    _dom_push_legacy_child_context(container, inst, cls)
    from ryact.hooks import _set_dom_effect_boundary_stack

    _set_dom_effect_boundary_stack(stack)
    try:
        try:
            return _render_to_virtual(
                rendered,
                portal_targets=portal_targets,
                container=container,
                parent_host_tag=parent_host_tag,
                ancestor_info=ancestor_info,
                host_parent_path=host_parent_path,
                next_child_index=next_child_index,
                class_render_depth=class_render_depth,
            )
        except BaseException as err:
            from .error_reporting import log_boundary_component_error

            dom_root = container._ryact_dom_root if container is not None else None
            rr = dom_root._reconciler_root if dom_root is not None else None
            for boundary in reversed(stack):
                did_catch = getattr(boundary, "componentDidCatch", None)
                gdsfe = getattr(type(boundary), "getDerivedStateFromError", None)
                if not (callable(did_catch) or callable(gdsfe)):
                    continue
                boundary_name = getattr(type(boundary), "__name__", "ErrorBoundary")
                deferred_log_err: BaseException | None = None
                try:
                    log_boundary_component_error(container, err, boundary_name=boundary_name)
                except BaseException as log_err:
                    deferred_log_err = log_err
                if callable(gdsfe):
                    partial = gdsfe(err)
                    if isinstance(partial, dict) and isinstance(getattr(boundary, "_state", None), dict):
                        boundary._state.update(partial)  # type: ignore[attr-defined]
                if callable(did_catch):
                    boundary._ryact_dom_in_did_catch = True  # type: ignore[attr-defined]
                    try:
                        did_catch(err)
                    finally:
                        boundary._ryact_dom_in_did_catch = False  # type: ignore[attr-defined]
                    if is_dev() and not callable(gdsfe):
                        from .error_reporting import log_console_error_message

                        log_console_error_message(
                            container,
                            f"{boundary_name}: Error boundaries should implement getDerivedStateFromError(). "
                            "In that method, return a state update to display an error message or fallback UI.",
                        )
                recovery = int(getattr(container, "_ryact_dom_error_recovery_count", 0) or 0) + 1
                container._ryact_dom_error_recovery_count = recovery  # type: ignore[attr-defined]
                if recovery > _NESTED_UPDATE_LIMIT:
                    raise RuntimeError(
                        "Maximum update depth exceeded. This can happen when a component repeatedly "
                        "calls setState inside componentWillUpdate or componentDidUpdate. React limits "
                        "the number of nested updates to prevent infinite loops."
                    ) from None
                if rr is not None:
                    _apply_queued_class_state_for_sync_render(boundary, rr, strict=False)
                if (
                    not callable(gdsfe)
                    and isinstance(getattr(boundary, "_state", None), dict)
                    and not boundary._state.get("error")  # type: ignore[attr-defined]
                ):
                    return []
                recovered = boundary.render()
                out = _dom_render_class_output(
                    container=container,
                    inst=boundary,
                    rendered=recovered,
                    portal_targets=portal_targets,
                    parent_host_tag=parent_host_tag,
                    ancestor_info=ancestor_info,
                    host_parent_path=host_parent_path,
                    next_child_index=next_child_index,
                    class_render_depth=class_render_depth,
                )
                if deferred_log_err is not None and container is not None:
                    deferred = getattr(container, "_ryact_dom_deferred_boundary_errors", None)
                    if not isinstance(deferred, list):
                        deferred = []
                        container._ryact_dom_deferred_boundary_errors = deferred  # type: ignore[attr-defined]
                    deferred.append(deferred_log_err)
                return out
            raise
    finally:
        _set_dom_effect_boundary_stack([])
        _dom_pop_legacy_child_context(container)
        if container is not None:
            container._ryact_dom_current_boundary = prev_current_boundary  # type: ignore[attr-defined]
        if is_boundary and stack and stack[-1] is inst:
            stack.pop()


def _render_to_virtual(
    node: Renderable,
    *,
    portal_targets: list[Any],
    container: Container | None = None,
    parent_host_tag: str | None = None,
    ancestor_info: AncestorInfoDev | None = None,
    host_parent_path: tuple[int, ...] = (),
    next_child_index: list[int] | None = None,
    class_render_depth: int = 0,
) -> list[RenderedNode]:
    if node is None or node is False:
        return []
    if isinstance(node, bool):
        return []
    if isinstance(node, (str, int, float)):
        return [RenderedText(text=str(node))]
    from ryact.element import _ReadonlyChildrenList

    if isinstance(node, _ReadonlyChildrenList):
        if not node:
            return []
        if len(node) == 1:
            return _render_to_virtual(
                node[0],
                portal_targets=portal_targets,
                container=container,
                parent_host_tag=parent_host_tag,
                ancestor_info=ancestor_info,
                host_parent_path=host_parent_path,
                next_child_index=next_child_index,
                class_render_depth=class_render_depth,
            )
        from ryact.concurrent import fragment

        return _render_to_virtual(
            fragment(*node),
            portal_targets=portal_targets,
            container=container,
            parent_host_tag=parent_host_tag,
            ancestor_info=ancestor_info,
            host_parent_path=host_parent_path,
            next_child_index=next_child_index,
            class_render_depth=class_render_depth,
        )
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
        if node.type == StrictMode:
            children = node.props.get("children", ())
            child = children[0] if isinstance(children, (list, tuple)) and children else children
            return _render_to_virtual(
                child,
                portal_targets=portal_targets,
                container=container,
                parent_host_tag=parent_host_tag,
                ancestor_info=ancestor_info,
                host_parent_path=host_parent_path,
                next_child_index=next_child_index,
            )
        if node.type == Offscreen:
            children = node.props.get("children", ())
            child = children[0] if isinstance(children, (list, tuple)) and children else children
            return _render_to_virtual(
                child,
                portal_targets=portal_targets,
                container=container,
                parent_host_tag=parent_host_tag,
                ancestor_info=ancestor_info,
                host_parent_path=host_parent_path,
                next_child_index=next_child_index,
            )
        if node.type == SuspenseList:
            out_sl: list[RenderedNode] = []
            children = node.props.get("children", ())
            for c in children:
                out_sl.extend(
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
            return out_sl
        if node.type == Portal:
            target = node.props.get("container")
            if target is not None:
                if container is None:
                    raise RuntimeError("Portal rendering requires a host Container (ops + reconciliation context).")
                if not any(t is target for t in portal_targets):
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
                _set_portal_namespace_inheritance(
                    portal_target=target,
                    main_container=container,
                    host_parent_path=host_parent_path,
                )
                _commit_children(
                    container=target,
                    parent=target.root,
                    next_children=next_portal,
                    path=[],
                    owner_stack="",
                )
                pending_bubbles = getattr(container, "_ryact_pending_portal_bubbles", None)
                if not isinstance(pending_bubbles, list):
                    pending_bubbles = []
                    container._ryact_pending_portal_bubbles = pending_bubbles  # type: ignore[attr-defined]
                pending_bubbles.append((target, host_parent_path))
                if _rendered_tree_has_click_listener(next_portal):

                    def _ios_tap_noop() -> None:
                        return None

                    target._ios_tap_onclick = _ios_tap_noop
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
        parent_ns_ctx, parent_tag_ctx = _peek_namespace_context(container)
        if container is not None:
            el_ns = namespace_for_host_child(
                parent_tag=parent_tag_ctx or parent_host_tag,
                parent_namespace=parent_ns_ctx,
                tag=tag_l,
            )
            _push_namespace_context(container, el_ns, tag_l)
        is_custom_el = _is_custom_element_dom_tag(node.type)
        raw_map = dict(node.props) if isinstance(node.props, Mapping) else {}
        host_in_prev = None
        if tag_l == "input" and path_enabled and container is not None and my_host_path is not None:
            cand = _lookup_host_element_at_path(container, my_host_path)
            if cand is not None and cand.tag.lower() == "input":
                host_in_prev = cand
                preserve_value_on_invalid_form_field_inplace(raw_map, host_in_prev)
                preserve_null_defaultvalue_inplace(raw_map, host_in_prev)
        props = _host_props_normalized(raw_map, node.type)
        dsh = props.get("dangerouslySetInnerHTML") or props.get("dangerously_set_inner_html")
        if tag_l in _VOID_TAGS and tag_l != "menuitem":
            if isinstance(dsh, dict) and dsh.get("__html") is not None:
                raise void_element_children_or_innerhtml_error(node.type)
            if node.props.get("children", ()):
                raise void_element_children_or_innerhtml_error(node.type)
        listeners: dict[str, list[Callable[[Any], None]]] = {}
        listeners_capture: dict[str, list[Callable[[Any], None]]] = {}
        custom_on_property_mode: frozenset[str] = frozenset()
        if is_custom_el and path_enabled and container is not None and my_host_path is not None:
            prev_host = _lookup_host_element_at_path(container, my_host_path)
            if prev_host is not None and prev_host.tag == node.type:
                custom_on_property_mode = prev_host.custom_on_listener_property_modes
        for prop, value in list(raw_map.items()):
            if is_custom_el:
                event_type = None
                if prop.startswith("on") and len(prop) > 2:
                    tail = prop[2:]
                    event_type = tail.lower() if tail else None
                is_capture = False
            else:
                event_type, is_capture = parse_event_listener_prop(prop)
                if event_type is None:
                    event_type = dom_event_type_for_listener_key(prop)
                    is_capture = False
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
                props.pop(prop, None)
                continue
            if value is False and prop.startswith("on") and is_dev():
                warnings.warn(
                    f"Expected `{prop}` listener to be a function, instead got a value of `false`.\n"
                    f"    in {node.type} (at **)",
                    UserWarning,
                    stacklevel=4,
                )
                props.pop(prop, None)
                continue
            if prop.startswith("on") and not callable(value) and not is_custom_el and is_dev():
                warnings.warn(
                    f"Expected `{prop}` listener to be a function, instead got a value of "
                    f"`{type(value).__name__}`.\n"
                    f"    in {node.type} (at **)",
                    UserWarning,
                    stacklevel=4,
                )
            is_fn_listener = is_event_listener_prop(prop, value) or (is_custom_el and callable(value))
            if is_fn_listener:
                bucket = listeners_capture if is_capture else listeners
                bucket.setdefault(event_type, []).append(cast(Callable[[Any], None], value))
                if is_custom_el and event_type in custom_on_property_mode:
                    props[prop] = None
                else:
                    props.pop(prop, None)
                continue

            # Non-function listener: attach a sentinel that raises when dispatched.
            def _raise(_evt: Any, v=value, p=prop) -> None:
                raise TypeError(f"Expected `{p}` listener to be a function, instead got {type(v)!r}")

            listeners.setdefault(event_type, []).append(_raise)
            props.pop(prop, None)

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
            children = process_select_element_children(raw_host, props, children, host_select_prev=host_sel_prev)
            strip_select_internal_props(props)
        elif tag_l == "textarea":
            host_ta_prev = None
            if path_enabled and container is not None and my_host_path is not None:
                cand = _lookup_host_element_at_path(container, my_host_path)
                if cand is not None and cand.tag.lower() == "textarea":
                    host_ta_prev = cand
            ta = process_textarea_element_children(raw_host, props, children, host_prev=host_ta_prev)
            children = ta.children
            textarea_controlled = ta.controlled
            textarea_host_default_value = ta.host_default_value
            strip_textarea_internal_props(props)

        child_slot = [0] if path_enabled else None
        child_prefix = my_host_path if path_enabled and my_host_path is not None else host_parent_path
        rendered_children: list[RenderedNode] = []
        if tag_l == "option":
            vis = list(_iter_visible_host_children(children))
            owner = _dom_stack_str()

            def _render_option_child(c: object) -> list[RenderedNode]:
                return _render_to_virtual(
                    c,
                    portal_targets=portal_targets,
                    container=container,
                    parent_host_tag=node.type,
                    ancestor_info=info_inside,
                    host_parent_path=child_prefix,
                    next_child_index=child_slot,
                )

            flat_label, had_callable = flatten_option_label_in_order(
                vis,
                render_one=_render_option_child,
                owner_stack=owner,
            )
            opt = process_option_children_after_render(
                raw=raw_map,
                props=props,
                owner_stack=owner,
                visible_children=vis,
                flattened_text=flat_label,
                had_callable_child=had_callable,
            )
            strip_option_internal_props(props)
            if opt.force_value_attr:
                props["value"] = opt.host_value
            rendered_children = list(opt.children)
        elif isinstance(dsh, dict) and dsh.get("__html") is not None:
            if children:
                raise ValueError("Can only set one of `children` or `props.dangerouslySetInnerHTML`.")
            # Mirror React DOM: innerHTML is a property assignment, not a child node.
            props["innerHTML"] = format_dangerously_inner_html_value_dev(dsh.get("__html"))
            children = ()
        elif (
            tag_l != "textarea" and tag_l != "option" and children and not (isinstance(dsh, dict) and dsh.get("__html"))
        ):
            props.pop("innerHTML", None)
        if tag_l != "option":
            host_owner_stack = _dom_stack_str() if is_dev() else ""
            visible_host_children = list(_iter_visible_host_children(children, owner_stack=host_owner_stack))
            for c in visible_host_children:
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
        try:
            from ryact.hooks import current_class_component_instance

            owner = current_class_component_instance()
            owner_id = id(owner) if owner is not None else None
            boundary = getattr(container, "_ryact_dom_current_boundary", None) if container is not None else None
            return [
                RenderedElement(
                    tag=node.type,
                    key=node.key,
                    ref=raw_element_ref(node),
                    props=props,
                    listeners=listeners,
                    listeners_capture=listeners_capture,
                    owner_stack=_dom_stack_str(),
                    component_owner_id=owner_id,
                    error_boundary=boundary,
                    custom_on_property_mode=custom_on_property_mode,
                    textarea_controlled=textarea_controlled,
                    textarea_host_default_value=textarea_host_default_value,
                    input_host_default_value=input_host_default_value,
                    children=rendered_children,
                )
            ]
        finally:
            if container is not None:
                _pop_namespace_context(container)

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
            dom_root = container._ryact_dom_root if container is not None else None
            next_id = dom_root._next_use_id if dom_root is not None else None
            from ryact.hooks import _is_class_component

            from .host_refs import attach_component_ref

            import inspect

            if inspect.isgeneratorfunction(node.type) and not _is_class_component(node.type):
                gen = node.type(**dict(node.props)) if node.props else node.type()
                from .children_expansion import expand_rendered_children

                owner_stack = _dom_stack_str() if is_dev() else ""
                rendered = expand_rendered_children(list(gen), owner_stack=owner_stack)
                from ryact.element import coerce_top_level_render_result

                rendered = coerce_top_level_render_result(rendered)
                return _render_to_virtual(
                    rendered,
                    portal_targets=portal_targets,
                    container=container,
                    parent_host_tag=parent_host_tag,
                    ancestor_info=ancestor_info,
                    host_parent_path=host_parent_path,
                    next_child_index=next_child_index,
                    class_render_depth=class_render_depth,
                )

            comp_ref = raw_element_ref(node)
            rendered: Any
            if _is_class_component(node.type) and dom_root is not None:
                from ryact import hooks as _hooks_mod

                comp_slot: int | None = None
                if next_child_index is not None:
                    comp_slot = next_child_index[0]
                    next_child_index[0] += 1
                parent_token = _dom_class_parent_owner_token(
                    container=container,
                    host_parent_path=host_parent_path,
                )
                cache_key = _dom_class_instance_cache_key(
                    node.type, node.key, parent_token, comp_slot
                )
                cached = dom_root._class_instances.get(cache_key)
                if cached is not None:
                    _dom_tag_class_error_boundary(container, cached)
                    props_for_instance = getattr(cached, "_props", None)
                    if not isinstance(props_for_instance, dict):
                        props_for_instance = dict(node.props)
                    old_props = dict(props_for_instance)
                    next_props = dict(node.props)
                    cached._ryact_dom_cache_key = cache_key  # type: ignore[attr-defined]
                    cached._ryact_dom_prev_props = dict(next_props)  # type: ignore[attr-defined]
                    prev_ctx_snap = getattr(cached, "_ryact_dom_cached_context", None)
                    if prev_ctx_snap is None:
                        prev_ctx_snap = getattr(cached, "_context", None)
                    next_ctx = _dom_peek_legacy_context(node.type, container)
                    has_legacy_ctx = _dom_has_legacy_context_types(node.type)
                    ctx_changed = has_legacy_ctx and prev_ctx_snap != next_ctx
                    from ryact.component import _shallow_equal

                    props_changed = not _shallow_equal(old_props, next_props)
                    cwrp = getattr(cached, "UNSAFE_componentWillReceiveProps", None)
                    if not callable(cwrp):
                        cwrp = getattr(cached, "componentWillReceiveProps", None)
                    ran_cwrp_this_update = False
                    cwrp_ran = getattr(container, "_ryact_dom_cwrp_ran", None)
                    if not isinstance(cwrp_ran, set):
                        cwrp_ran = set()
                        container._ryact_dom_cwrp_ran = cwrp_ran  # type: ignore[attr-defined]
                    if callable(cwrp) and (
                        props_changed
                        or (ctx_changed and has_legacy_ctx)
                        or (
                            getattr(cached, "_ryact_did_mount", False)
                            and cached not in cwrp_ran
                            and bool(getattr(container, "_ryact_dom_user_commit", False))
                        )
                    ):
                        if getattr(cached, "_ryact_did_mount", False):
                            cwrp_ran.add(cached)
                        ran_cwrp_this_update = True
                        cached._ryact_dom_suppress_dirty = True  # type: ignore[attr-defined]
                        cached._ryact_dom_in_cwrp = True  # type: ignore[attr-defined]
                        _hooks_mod._enter_component_render(name)
                        try:
                            import inspect

                            cwrp_next_props = next_props if props_changed else props_for_instance
                            cwrp_n = len(inspect.signature(cwrp).parameters)
                            cwrp_ctx = _dom_cwrp_context(
                                cached, has_legacy_ctx=has_legacy_ctx, next_ctx=next_ctx
                            )
                            _call_legacy_will_receive_props(
                                cwrp,
                                cwrp_next_props,
                                cwrp_ctx,
                                has_ctx=cwrp_n >= 2,
                            )
                        finally:
                            _hooks_mod._exit_component_render()
                            cached._ryact_dom_in_cwrp = False  # type: ignore[attr-defined]
                    _dom_apply_class_instance_context(cached, node.type, container)
                    cached._ryact_dom_cached_context = next_ctx  # type: ignore[attr-defined]
                    cached._props = next_props if props_changed else props_for_instance  # type: ignore[attr-defined]
                    rr = dom_root._reconciler_root
                    prev_state_snap = _dom_class_state_dict(cached)
                    if not bool(getattr(rr, "_batched_legacy_flush", False)):
                        _apply_queued_class_state_for_sync_render(cached, rr, strict=False)
                    if getattr(cached, "_ryact_did_mount", False):
                        prev_props_snap = dict(old_props)
                        next_props = dict(cached._props)  # type: ignore[attr-defined]
                        next_state = _dom_class_state_dict(cached)
                        cached._ryact_dom_cdu_prev = (prev_props_snap, prev_state_snap)  # type: ignore[attr-defined]
                        cached._ryact_dom_pending_cdu = True  # type: ignore[attr-defined]
                        cdu_order = getattr(container, "_ryact_dom_cdu_order", None)
                        if not isinstance(cdu_order, list):
                            cdu_order = []
                            container._ryact_dom_cdu_order = cdu_order  # type: ignore[attr-defined]
                        if cached not in cdu_order:
                            cdu_order.append(cached)
                        cdu_depth = getattr(container, "_ryact_dom_cdu_depth", None)
                        if not isinstance(cdu_depth, dict):
                            cdu_depth = {}
                            container._ryact_dom_cdu_depth = cdu_depth  # type: ignore[attr-defined]
                        cdu_depth[cached] = class_render_depth
                        _hooks_mod._enter_component_render(name)
                        try:
                            cwup = getattr(cached, "componentWillUpdate", None)
                            if callable(cwup):
                                _call_legacy_will_update(
                                    cwup, next_props, next_state, next_ctx, has_ctx=has_legacy_ctx
                                )
                            cwu = getattr(cached, "UNSAFE_componentWillUpdate", None)
                            if callable(cwu):
                                _call_legacy_will_update(
                                    cwu, next_props, next_state, next_ctx, has_ctx=has_legacy_ctx
                                )
                        finally:
                            _hooks_mod._exit_component_render()
                    _wire_dom_class_schedule_update(container, cached)
                    if comp_ref is not None:
                        attach_component_ref(cached, comp_ref)
                    with _StackFrame(name):
                        prev_inst = _hooks_mod._current_class_component_instance
                        _hooks_mod._current_class_component_instance = cached
                        try:
                            _dom_warn_class_legacy_context_dev(node.type, name)
                            ctx_unchanged = prev_ctx_snap == next_ctx
                            cached._ryact_dom_cached_context = next_ctx  # type: ignore[attr-defined]
                            _hooks_mod._enter_component_render(name)
                            try:
                                props_unchanged = old_props == dict(cached._props)
                                state_snap = _dom_class_state_dict(cached)
                                state_unchanged = state_snap == getattr(cached, "_ryact_dom_cached_state", None)
                                scu_bailed = False
                                scu = getattr(cached, "shouldComponentUpdate", None)
                                if (
                                    callable(scu)
                                    and getattr(cached, "_ryact_did_mount", False)
                                    and not getattr(cached, "_force_update", False)
                                ):
                                    import inspect

                                    prev_props_for_scu = dict(old_props)
                                    prev_state_obj = getattr(cached, "_ryact_dom_cached_state", None)
                                    prev_state_for_scu = (
                                        dict(prev_state_obj) if isinstance(prev_state_obj, dict) else {}
                                    )
                                    next_props_for_scu = dict(cached._props)  # type: ignore[attr-defined]
                                    next_state_for_scu = _peek_merged_class_state_dict(cached, rr)
                                    scu_n = len(inspect.signature(scu).parameters)
                                    cached._props = prev_props_for_scu  # type: ignore[attr-defined]
                                    if isinstance(getattr(cached, "_state", None), dict):
                                        cached._state = dict(prev_state_for_scu)  # type: ignore[attr-defined]
                                    try:
                                        if has_legacy_ctx and scu_n >= 3:
                                            should_update = bool(
                                                scu(next_props_for_scu, next_state_for_scu, next_ctx)
                                            )
                                        elif scu_n >= 3:
                                            should_update = bool(
                                                scu(
                                                    next_props_for_scu,
                                                    next_state_for_scu,
                                                    _dom_cwrp_context(
                                                        cached, has_legacy_ctx=False, next_ctx=next_ctx
                                                    ),
                                                )
                                            )
                                        else:
                                            should_update = bool(scu(next_props_for_scu, next_state_for_scu))
                                    finally:
                                        cached._props = next_props_for_scu  # type: ignore[attr-defined]
                                        if isinstance(getattr(cached, "_state", None), dict):
                                            cached._state = dict(next_state_for_scu)  # type: ignore[attr-defined]
                                    if not should_update:
                                        _apply_queued_class_state_for_sync_render(cached, rr, strict=False)
                                        cached._ryact_dom_cached_state = _dom_class_state_dict(cached)  # type: ignore[attr-defined]
                                        rendered = getattr(cached, "_ryact_dom_cached_rendered", None)
                                        scu_bailed = True
                                if not scu_bailed and not ran_cwrp_this_update and (
                                    class_render_depth > 0
                                    and getattr(cached, "_ryact_did_mount", False)
                                    and props_unchanged
                                    and state_unchanged
                                    and ctx_unchanged
                                    and getattr(cached, "_ryact_dom_render_stabilized", False)
                                    and not getattr(cached, "_force_update", False)
                                    and not bool(getattr(container, "_ryact_dom_user_commit", False))
                                ):
                                    rendered = getattr(cached, "_ryact_dom_cached_rendered", None)
                                elif not scu_bailed:
                                    rendered = cached.render()
                                    cached._ryact_dom_render_stabilized = True  # type: ignore[attr-defined]
                                    cached._ryact_dom_cached_rendered = rendered  # type: ignore[attr-defined]
                                    cached._ryact_dom_cached_state = state_snap  # type: ignore[attr-defined]
                                cached._force_update = False  # type: ignore[attr-defined]
                                if not scu_bailed:
                                    rr_cached = dom_root._reconciler_root
                                    if getattr(cached, "_ryact_dom_skip_post_render_state_loop", False):
                                        cached._ryact_dom_skip_post_render_state_loop = False  # type: ignore[attr-defined]
                                    else:
                                        for _ in range(_NESTED_UPDATE_LIMIT + 1):
                                            pending = getattr(cached, "_pending_state_updates", None)
                                            if not isinstance(pending, list) or not pending:
                                                break
                                            if bool(getattr(rr_cached, "_batched_legacy_flush", False)):
                                                break
                                            state_before = _dom_class_state_dict(cached)
                                            _apply_queued_class_state_for_sync_render(cached, rr_cached, strict=False)
                                            if _dom_class_state_dict(cached) == state_before:
                                                pending.clear()
                                                break
                                            _hooks_mod._enter_component_render(name)
                                            try:
                                                rendered = cached.render()
                                            finally:
                                                _hooks_mod._exit_component_render()
                            finally:
                                _hooks_mod._exit_component_render()
                        finally:
                            _hooks_mod._current_class_component_instance = prev_inst
                else:
                    _dom_warn_class_legacy_context_dev(node.type, name)
                    layout_effs, passive_effs = _dom_effect_lists(container)

                    def _dom_run_cwm_before_render(inst0: Any) -> None:
                        for cwm_name in ("componentWillMount", "UNSAFE_componentWillMount"):
                            cwm = getattr(inst0, cwm_name, None)
                            if callable(cwm):
                                inst0._ryact_pre_mount_phase = True  # type: ignore[attr-defined]
                                _hooks_mod._enter_component_render(name)
                                try:
                                    cwm()
                                finally:
                                    _hooks_mod._exit_component_render()
                                    inst0._ryact_pre_mount_phase = False  # type: ignore[attr-defined]
                                inst0._ryact_pending_mount = True  # type: ignore[attr-defined]
                                break

                    class_inst: list[Any] = []
                    rendered = _render_component(
                        node.type,
                        dict(node.props),
                        _get_component_hooks(node.type),
                        schedule_update=_dom_function_schedule_update(container),
                        default_lane=DEFAULT_LANE,
                        next_id=next_id,
                        class_instance_out=class_inst,
                        defer_render_phase_restart=True,
                        legacy_merged=_dom_legacy_merged(container),
                        scheduled_layout_effects=layout_effs,
                        scheduled_passive_effects=passive_effs,
                        before_render=_dom_run_cwm_before_render,
                    )
                    inst0 = class_inst[0]
                    _dom_tag_class_error_boundary(container, inst0)
                    inst0._ryact_dom_cache_key = cache_key  # type: ignore[attr-defined]
                    inst0._ryact_dom_prev_props = dict(node.props)  # type: ignore[attr-defined]
                    dom_root._class_instances[cache_key] = inst0
                    _wire_dom_class_schedule_update(container, inst0)
                    rr_new = dom_root._reconciler_root
                    for _ in range(_NESTED_UPDATE_LIMIT + 1):
                        pending = getattr(inst0, "_pending_state_updates", None)
                        if not isinstance(pending, list) or not pending:
                            break
                        if bool(getattr(rr_new, "_batched_legacy_flush", False)):
                            break
                        state_before = _dom_class_state_dict(inst0)
                        _apply_queued_class_state_for_sync_render(inst0, rr_new, strict=False)
                        if _dom_class_state_dict(inst0) == state_before:
                            pending.clear()
                            break
                        _hooks_mod._enter_component_render(name)
                        try:
                            rendered = inst0.render()
                        finally:
                            _hooks_mod._exit_component_render()
                    inst0._ryact_dom_render_stabilized = True  # type: ignore[attr-defined]
                    inst0._ryact_dom_cached_rendered = rendered  # type: ignore[attr-defined]
                    inst0._ryact_dom_cached_state = _dom_class_state_dict(inst0)  # type: ignore[attr-defined]
                    inst0._ryact_dom_cached_context = _dom_peek_legacy_context(node.type, container)  # type: ignore[attr-defined]
                    if comp_ref is not None:
                        attach_component_ref(inst0, comp_ref)
                snap = container._form_status_snapshot
                if isinstance(snap, FormStatusSnapshot) and snap.pending:
                    rendered = form_status_provider(snap, rendered)
                virt_inst = dom_root._class_instances.get(cache_key)
                if virt_inst is not None:
                    stack = getattr(container, "_ryact_commit_class_stack", None)
                    if not isinstance(stack, list):
                        stack = []
                        container._ryact_commit_class_stack = stack  # type: ignore[attr-defined]
                    stack.append(virt_inst)
                    with _StackFrame(name):
                        prev_inst = _hooks_mod._current_class_component_instance
                        _hooks_mod._current_class_component_instance = virt_inst
                        try:
                            return _dom_render_class_output(
                                container=container,
                                inst=virt_inst,
                                rendered=rendered,
                                portal_targets=portal_targets,
                                parent_host_tag=parent_host_tag,
                                ancestor_info=ancestor_info,
                                host_parent_path=host_parent_path,
                                next_child_index=next_child_index,
                                class_render_depth=class_render_depth + 1,
                            )
                        finally:
                            _hooks_mod._current_class_component_instance = prev_inst
            else:
                fn_stack = getattr(container, "_ryact_fn_render_stack", None) if container is not None else None
                if container is not None and not isinstance(fn_stack, list):
                    fn_stack = []
                    container._ryact_fn_render_stack = fn_stack  # type: ignore[attr-defined]
                if isinstance(fn_stack, list):
                    fn_stack.append(id(node.type))
                _dom_warn_function_component_dev(node.type, name)
                layout_effs, passive_effs = _dom_effect_lists(container)
                rendered = _render_component(
                    node.type,
                    dict(props_for_component_render(node.type, node.props)),
                    _get_component_hooks(node.type),
                    schedule_update=_dom_function_schedule_update(container),
                    default_lane=DEFAULT_LANE,
                    next_id=next_id,
                    class_instance_out=None,
                    defer_render_phase_restart=True,
                    legacy_context=_dom_legacy_context_for_hooks(container, node.type),
                    scheduled_layout_effects=layout_effs,
                    scheduled_passive_effects=passive_effs,
                )
                snap = container._form_status_snapshot
                if isinstance(snap, FormStatusSnapshot) and snap.pending:
                    rendered = form_status_provider(snap, rendered)
                try:
                    return _dom_render_function_component_output(
                        rendered=rendered,
                        component_name=name,
                        container=container,
                        portal_targets=portal_targets,
                        parent_host_tag=parent_host_tag,
                        ancestor_info=ancestor_info,
                        host_parent_path=host_parent_path,
                        next_child_index=next_child_index,
                        class_render_depth=class_render_depth,
                    )
                finally:
                    if isinstance(fn_stack, list) and fn_stack and fn_stack[-1] == id(node.type):
                        fn_stack.pop()

    raise TypeError(f"Unsupported element type: {node.type!r}")


def _dom_class_instance_for_owner_id(container: Container, owner_id: int | None) -> Any | None:
    if owner_id is None:
        return None
    dom_root = getattr(container, "_ryact_dom_root", None)
    if dom_root is None:
        return None
    for inst in dom_root._class_instances.values():
        if id(inst) == owner_id:
            return inst
    return None


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
        is_opt = v.props.get("is")
        if isinstance(is_opt, str) and is_opt.strip():
            el._document_create_options = {"is": is_opt}
        from ryact.hooks import current_class_component_instance

        inst = None
        if isinstance(v, RenderedElement):
            inst = _dom_class_instance_for_owner_id(container, v.component_owner_id)
        if inst is None:
            stack = getattr(container, "_ryact_commit_class_stack", None)
            inst = stack[-1] if isinstance(stack, list) and stack else None
        if inst is None:
            inst = current_class_component_instance()
        if inst is not None:
            from .dom_internals import link_component_dom_host

            link_component_dom_host(inst, el)
        el._listeners = {k: list(vs) for k, vs in v.listeners.items()}
        el._listeners_capture = {k: list(vs) for k, vs in v.listeners_capture.items()}
        el._event_container = container
        if isinstance(v, RenderedElement) and v.error_boundary is not None:
            el._ryact_dom_error_boundary = v.error_boundary  # type: ignore[attr-defined]
        el.custom_on_listener_property_modes = v.custom_on_property_mode
        if v.tag.lower() == "textarea":
            el._textarea_controlled = v.textarea_controlled
            el._textarea_host_default_value = v.textarea_host_default_value
        if v.tag.lower() == "input" and v.input_host_default_value is not None:
            el._input_host_default_value = v.input_host_default_value
        sync_host_style_from_props(el)
        if v.tag.lower() == "input":
            init_input_host_on_mount(el)
        if v.tag.lower() == "option":
            init_option_host_on_mount(el)
        from .form_actions import apply_action_fn_fields_from_props

        apply_action_fn_fields_from_props(el)
        parent_ns = parent._namespace_uri if isinstance(parent, ElementNode) else None
        parent_tag_for_ns = parent.tag if isinstance(parent, ElementNode) else None
        if isinstance(parent, ElementNode) and parent.tag == "root":
            inh_ns = getattr(container, "_ryact_portal_parent_namespace", None)
            if inh_ns is not None:
                parent_ns = inh_ns
                parent_tag_for_ns = getattr(container, "_ryact_portal_parent_tag", None)
        el._namespace_uri = namespace_for_host_child(
            parent_tag=parent_tag_for_ns,
            parent_namespace=parent_ns,
            tag=el.tag,
        )
        autofocus_host_if_needed(el)
        from .host_refs import commit_host_ref

        commit_host_ref(el, v.ref)
        return el

    def can_reuse(prev: Node, nxt: RenderedNode) -> bool:
        if isinstance(prev, TextNode) and isinstance(nxt, RenderedText):
            return True
        if isinstance(prev, ElementNode) and isinstance(nxt, RenderedElement):
            if prev.tag != nxt.tag or prev.key != nxt.key:
                return False
            owner = getattr(prev, "_ryact_component_owner", None)
            if owner is not None:
                from ryact.hooks import current_class_component_instance

                stack = getattr(container, "_ryact_commit_class_stack", None)
                top = stack[-1] if isinstance(stack, list) and stack else None
                active = top or current_class_component_instance()
                if active is None or id(active) != owner:
                    return False
            return True
        return False

    def apply_updates(node: Node, nxt: RenderedNode, p: list[int]) -> None:
        if isinstance(node, TextNode) and isinstance(nxt, RenderedText):
            if node.text != nxt.text:
                node.text = nxt.text
                _op(container, {"op": "text", "path": list(p), "value": nxt.text})
            return
        if isinstance(node, ElementNode) and isinstance(nxt, RenderedElement):
            from ryact.hooks import current_class_component_instance

            inst = _dom_class_instance_for_owner_id(container, nxt.component_owner_id)
            if inst is None:
                stack = getattr(container, "_ryact_commit_class_stack", None)
                inst = stack[-1] if isinstance(stack, list) and stack else None
            if inst is None:
                inst = current_class_component_instance()
            if inst is not None:
                from .dom_internals import link_component_dom_host

                link_component_dom_host(inst, node)
            if nxt.tag.lower() == "textarea" and node._textarea_controlled and not nxt.textarea_controlled:
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
                and _raw_input_type_lower(nxt.props) not in ("reset", "submit", "radio", "checkbox")
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
                        and _raw_input_type_lower(nxt.props) not in ("radio", "checkbox")
                    )
                    or (
                        _input_is_checkbox_or_radio(tag_l=nxt.tag.lower(), props=nxt.props)
                        and "checked" in nxt.props
                        and ("checked" not in node.props or node.props.get("checked") is None)
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
                prev_input_host_default = node._input_host_default_value
                node._input_host_default_value = nxt.input_host_default_value
            else:
                prev_input_host_default = None
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
                    if k == "id":
                        continue
                    removed.append(k)
            prev_props_snapshot = dict(node.props)
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
            if nxt.tag.lower() == "input":
                sync_input_host_after_props_update(
                    node,
                    prev_props=prev_props_snapshot,
                    prev_host_default=prev_input_host_default if nxt.input_host_default_value is not None else None,
                )
            if nxt.tag.lower() == "option":
                sync_option_host_after_props_update(node, prev_props=prev_props_snapshot)
            dsh_nxt = nxt.props.get("dangerouslySetInnerHTML") or nxt.props.get("dangerously_set_inner_html")
            if (isinstance(dsh_nxt, dict) and dsh_nxt.get("__html") is not None) or nxt.children:
                node._inner_html_preserved = None
            sync_host_style_from_props(node)
            node._listeners = {k: list(vs) for k, vs in nxt.listeners.items()}
            node._listeners_capture = {k: list(vs) for k, vs in nxt.listeners_capture.items()}
            node._event_container = container
            node.custom_on_listener_property_modes = nxt.custom_on_property_mode
            from .form_actions import apply_action_fn_fields_from_props

            apply_action_fn_fields_from_props(node)
            _commit_children(
                container=container,
                parent=node,
                next_children=nxt.children,
                path=list(p) + [0],
                owner_stack=nxt.owner_stack,
            )
            from .host_refs import commit_host_ref

            commit_host_ref(node, nxt.ref)
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
                    _detach_host_subtree(c3)
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
            _detach_host_subtree(prev)
            n = make_node(nxt)
            next_nodes2.append(n)
            payload: dict[str, Any] = {
                "op": "insert",
                "path": list(path) + [i],
                "tag": getattr(n, "tag", "#text"),
                "key": None,
            }
            if isinstance(n, ElementNode) and n._document_create_options:
                payload["createOptions"] = dict(n._document_create_options)
            _op(container, payload)

    # Inserts
    for i in range(min_len, len(next_children)):
        nxt = next_children[i]
        n = make_node(nxt)
        next_nodes2.append(n)
        payload2: dict[str, Any] = {
            "op": "insert",
            "path": list(path) + [i],
            "tag": getattr(n, "tag", "#text"),
            "key": None,
        }
        if isinstance(n, ElementNode) and n._document_create_options:
            payload2["createOptions"] = dict(n._document_create_options)
        _op(container, payload2)

    # Deletes
    for i in range(len(next_children), len(prev_children)):
        _detach_host_subtree(prev_children[i])
        _op(container, {"op": "delete", "path": list(path) + [i]})

    parent.children = next_nodes2
    for i, (n, v) in enumerate(zip(parent.children, next_children, strict=True)):
        n.parent = parent
        apply_updates(n, v, list(path) + [i])


def _first_host_node(container: Container) -> ElementNode | None:
    for ch in container.root.children:
        if isinstance(ch, ElementNode):
            return ch
    return None


def _dom_class_state_dict(instance: Any) -> dict[str, Any]:
    st = getattr(instance, "_state", None)
    return dict(st) if isinstance(st, dict) else {}


def _run_dom_class_did_update_if_needed(
    instance: Any,
    *,
    container: Container | None = None,
) -> None:
    if not getattr(instance, "_ryact_dom_pending_cdu", False):
        return
    instance._ryact_dom_pending_cdu = False  # type: ignore[attr-defined]
    prev = getattr(instance, "_ryact_dom_cdu_prev", None)
    if not isinstance(prev, tuple) or len(prev) != 2:
        return
    prev_props, prev_state = prev
    cb = getattr(instance, "componentDidUpdate", None)
    if callable(cb):
        pending = getattr(instance, "_pending_state_updates", None)
        pending_len = len(pending) if isinstance(pending, list) else 0
        try:
            cb(prev_props, prev_state)
        except BaseException as err:
            if container is not None and _dom_handle_lifecycle_error(
                container,
                instance,
                err,
                prefer_first_captured_error=False,
            ):
                return
            if container is not None:
                _dom_report_or_reraise_uncaught(container, err)
                return
            raise
        pending_after = getattr(instance, "_pending_state_updates", None)
        if (
            isinstance(pending_after, list)
            and len(pending_after) > pending_len
            and container is not None
            and container._ryact_dom_root is not None
            and not bool(getattr(container._ryact_dom_root._reconciler_root, "_is_batching_updates", False))
        ):
            from ryact.reconciler import _check_nested_update_depth

            _check_nested_update_depth(container._ryact_dom_root._reconciler_root)


def _ensure_class_instances_mounted(root: Root) -> None:
    from .dom_internals import _flush_class_setstate_callbacks, _run_class_mount_if_needed

    container = root.container
    container._ryact_dom_in_mount_commit = True  # type: ignore[attr-defined]
    try:
        instances = list(root._class_instances.values())
        cdu_order = getattr(container, "_ryact_dom_cdu_order", None)
        if isinstance(cdu_order, list) and cdu_order:
            depth_map = getattr(container, "_ryact_dom_cdu_depth", None)
            if isinstance(depth_map, dict):
                cdu_work = sorted(cdu_order, key=lambda inst: depth_map.get(inst, 0), reverse=True)
            else:
                cdu_work = list(reversed(list(cdu_order)))
            cdu_order.clear()
            if isinstance(depth_map, dict):
                for inst in cdu_work:
                    depth_map.pop(inst, None)
        else:
            cdu_work = list(instances)
        for inst in cdu_work:
            _run_dom_class_did_update_if_needed(inst, container=container)
        for inst in instances:
            _flush_class_setstate_callbacks(inst)
        mount_errors: list[BaseException] = []
        for inst in instances:
            if not getattr(inst, "_ryact_did_mount", False):
                try:
                    _run_class_mount_if_needed(inst, container=container)
                except BaseException as err:
                    if _dom_handle_lifecycle_error(
                        container,
                        inst,
                        err,
                        prefer_first_captured_error=True,
                    ):
                        break
                    mount_errors.append(err)
        if len(mount_errors) > 1:
            _dom_raise_collected_errors(mount_errors, label="commit errors")
        elif len(mount_errors) == 1:
            from .error_reporting import _is_legacy_container

            err = mount_errors[0]
            if _is_legacy_container(container) or (
                isinstance(err, RuntimeError) and "Maximum update depth exceeded" in str(err)
            ):
                raise err
    finally:
        container._ryact_dom_in_mount_commit = False  # type: ignore[attr-defined]
    rr = root._reconciler_root
    commit = getattr(rr, "_commit_fn", None)
    if callable(commit) and rr.pending_updates and rr.scheduler is None:
        if bool(getattr(container, "_ryact_dom_in_full_commit", False)):
            dirty = getattr(container, "_ryact_dom_mount_dirty", None)
            if not isinstance(dirty, list):
                dirty = []
                container._ryact_dom_mount_dirty = dirty  # type: ignore[attr-defined]
            for inst in root._class_instances.values():
                pending = getattr(inst, "_pending_state_updates", None)
                if isinstance(pending, list) and pending and inst not in dirty:
                    dirty.append(inst)
        else:
            from ryact.reconciler import perform_work

            perform_work(rr, commit)


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

    if host_parent.children and is_dev():
        warn_replacing_react_children_with_new_root()
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
                    if not any(t is target for t in portal_targets):
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
    _has_committed: bool = False
    _last_rendered_element: Element | None = None
    _next_use_id: Callable[[], str] | None = None
    _legacy_render_callback: Callable[[], None] | None = None
    _class_instances: dict[tuple[Any, str | None], Any] = field(default_factory=dict)

    def flush_sync(self, fn: Callable[[], Any] | None = None) -> None:
        """``ReactDOM.flushSync`` — force synchronous commit (createRoot / legacy reconciler roots)."""

        from contextlib import suppress

        from ryact.concurrent import _with_update_lane

        import ryact.hooks as _hooks_mod

        rr = self._reconciler_root
        in_flush = int(getattr(rr, "_flush_depth", 0) or 0) > 0
        in_lifecycle_commit = bool(getattr(self.container, "_ryact_dom_in_mount_commit", False))
        if (
            (in_flush or in_lifecycle_commit)
            and _hooks_mod._current_commit_phase != "passive"
        ):
            if is_dev():
                from .error_reporting import log_console_error_message

                log_console_error_message(
                    self.container,
                    "flushSync was called from inside a lifecycle method. React cannot flush when "
                    "React is already rendering. Consider moving this call to a scheduler task or "
                    "micro task.\n"
                    "    in Component (at **)",
                )
            return
        prev = getattr(rr, "_force_sync_updates", False)
        rr._force_sync_updates = True  # type: ignore[attr-defined]
        stashed: list[Update] = []
        el_before = getattr(rr, "_last_element", None)
        if getattr(rr, "scheduler", None) is None and fn is not None:
            stashed = list(getattr(rr, "pending_updates", []))
            with suppress(Exception):
                rr.pending_updates.clear()
        try:
            with _with_update_lane(SYNC_LANE):
                if fn is not None:
                    fn()
                if _hooks_mod._current_commit_phase == "passive":
                    from ryact.reconciler import _check_nested_update_depth

                    try:
                        _check_nested_update_depth(rr)
                    except RuntimeError as err:
                        if "Maximum update depth exceeded" in str(err):
                            from .error_reporting import report_uncaught_error

                            report_uncaught_error(self.container, err)
                            return
                        raise
                commit = getattr(rr, "_commit_fn", None)
                if callable(commit):
                    perform_work(rr, commit)
        finally:
            rr._force_sync_updates = prev  # type: ignore[attr-defined]
        if stashed and getattr(rr, "scheduler", None) is None and fn is not None:
            el_after = getattr(rr, "_last_element", None)
            if el_after is not el_before:
                stashed = [
                    u
                    for u in stashed
                    if not (isinstance(u, Update) and isinstance(u.payload, Element) and u.payload is not el_after)
                ]
            with suppress(Exception):
                rr.pending_updates.extend(stashed)

    def unmount(self, *extra: Any) -> None:
        if extra:
            warn_unmount_extra_callback()
        if self._unmounted:
            raise RuntimeError("Cannot unmount a root that has already been unmounted.")
        if self._has_committed and not self.container.root.children:
            raise RuntimeError("The node to be removed is not a child of this node.")
        if _root_render_depth > 0 and is_dev():
            warnings.warn(
                "Attempted to synchronously unmount a root while React was already rendering. "
                "React cannot finish unmounting the root until the current render has completed, "
                "which may lead to a race condition.\n"
                "    in App (at **)",
                UserWarning,
                stacklevel=2,
            )
        rr = self._reconciler_root
        self.render(None)
        self._unmounted = True
        unregister_root_for_container(self.container)
        rr.pending_updates.clear()
        for host in list(self._portal_targets or []):
            if hasattr(host, "root"):
                for ch in list(host.root.children):
                    _detach_host_subtree(ch)
                host.root.children.clear()
        self._portal_targets = None
        from .dom_internals import clear_component_dom_node

        for inst in list(self._class_instances.values()):
            clear_component_dom_node(inst)
        self._class_instances.clear()
        for ch in list(self.container.root.children):
            _detach_host_subtree(ch)
        self.container.root.children.clear()
        self.container.ops.clear()

    def render(self, element: Element | None, *extra: Any, lane: Lane = DEFAULT_LANE) -> None:
        if extra:
            arg = extra[0]
            if callable(arg) and not isinstance(arg, Element):
                warn_render_extra_callback()
            elif isinstance(arg, Container):
                warn_render_extra_argument("container")
            else:
                warn_render_extra_argument("object")
        if self._unmounted:
            raise RuntimeError("Cannot update an unmounted root.")
        self._last_rendered_element = element if isinstance(element, Element) else None
        if element is not None and not isinstance(element, Element):
            if callable(element):
                warn_render_invalid_child("function", detail="\n  root.render(Component)")
            else:
                warn_render_invalid_child("symbol", detail=f"\n  root.render({element!r})")
            element = None
        ensure_selectionchange_subscription()

        def _root_component_type(el: Element | None) -> Any:
            if isinstance(el, Element) and callable(el.type):
                from ryact.hooks import _is_class_component

                if _is_class_component(el.type):
                    return el.type
            return None

        new_root_type = _root_component_type(element)
        prev_root_type = getattr(self, "_root_component_type", None)
        if (
            new_root_type is not None
            and prev_root_type is not None
            and new_root_type is not prev_root_type
        ):
            from .dom_internals import clear_component_dom_node

            for inst in list(self._class_instances.values()):
                clear_component_dom_node(inst)
            self._class_instances.clear()
        if new_root_type is not None:
            self._root_component_type = new_root_type  # type: ignore[attr-defined]
        elif element is None:
            self._root_component_type = None  # type: ignore[attr-defined]

        if bool(getattr(self.container, "_ryact_dom_in_mount_commit", False)) or bool(
            getattr(self.container, "_ryact_dom_in_full_commit", False)
        ):
            from ryact.reconciler import _check_nested_update_depth

            _check_nested_update_depth(self._reconciler_root)

        global _root_render_depth
        _root_render_depth += 1

        def commit(payload: Any) -> None:
            from .legacy_mount import is_legacy_container
            from .root_dev import _container_active_root

            if self._unmounted:
                return
            if not is_legacy_container(self.container) and _container_active_root.get(
                id(self.container)
            ) is not self:
                return
            preserve_focus_before_commit()
            preserved_radio_checked: list[tuple[Any, Any, bool]] = []
            if self._hydrating:
                # Minimal hydration slice: compare existing host tree with next payload and
                # report a recoverable mismatch, then replace.
                for inp in self.container.query_selector_all("input"):
                    if str(inp.props.get("type", "")).lower() == "radio" and inp.checked:
                        preserved_radio_checked.append((inp.props.get("name"), inp.props.get("value"), True))
                try:
                    _detect_hydration_mismatch(self.container, payload)
                except Exception as err:
                    if is_dev():
                        warnings.warn(
                            "A tree hydrated but some attributes of the server rendered HTML didn't "
                            "match the client properties. This won't be patched up. This can happen "
                            "if a SSR-ed Client Component used:\n\n"
                            "- A server/client branch `if (typeof window !== 'undefined')`.\n"
                            "- Variable input such as `Date.now()` or `Math.random()` which changes "
                            "each time it's called.\n"
                            "- Date formatting in a user's locale which doesn't match the server.\n"
                            "- External changing data without sending a snapshot of it along with "
                            "the HTML.\n"
                            "- Invalid HTML tag nesting.\n\n"
                            "It can also happen if the client has a browser extension installed "
                            "which messes with the HTML before React loaded.\n\n"
                            "https://react.dev/link/hydration-mismatch\n\n"
                            "  <span>\n"
                            "  <span>\n\n"
                            "    in span (at **)",
                            UserWarning,
                            stacklevel=2,
                        )
                    if self._on_recoverable_error is not None:
                        self._on_recoverable_error(err)
            # Phase 24: incremental commit into existing host tree (primary root + portal targets).
            self.container.ops.clear()
            _reset_namespace_context_stack(self.container)
            prev_portals = list(self._portal_targets or [])
            portal_targets: list[Any] = []
            self.container._ryact_dom_mount_dirty = []  # type: ignore[attr-defined]
            self.container._ryact_dom_cwrp_ran = set()  # type: ignore[attr-defined]
            self.container._ryact_dom_legacy_stack = [{}]  # type: ignore[attr-defined]
            self.container._ryact_dom_error_recovery_count = 0  # type: ignore[attr-defined]
            _reset_dom_effect_lists(self.container)
            from ryact.reconciler import _check_nested_update_depth

            self.container._ryact_dom_in_full_commit = True  # type: ignore[attr-defined]
            try:
                next_v: list[RenderedNode] = []
                for _ in range(_NESTED_UPDATE_LIMIT + 1):
                    for _ in range(_NESTED_UPDATE_LIMIT + 1):
                        try:
                            next_v = _render_to_virtual(
                                payload,
                                portal_targets=portal_targets,
                                container=self.container,
                                parent_host_tag=None,
                                host_parent_path=(),
                                next_child_index=[0],
                            )
                        except BaseException as err:
                            from .error_reporting import _is_legacy_container, report_uncaught_error

                            report_uncaught_error(self.container, err)
                            if _is_legacy_container(self.container) or (
                                isinstance(err, RuntimeError)
                                and "Maximum update depth exceeded" in str(err)
                            ):
                                raise
                            if (
                                not self._has_committed
                                and bool(getattr(rr, "_is_batching_updates", False))
                            ):
                                raise err
                            next_v = []
                            break
                        dirty_mount = getattr(self.container, "_ryact_dom_mount_dirty", None)
                        if isinstance(dirty_mount, list) and dirty_mount:
                            if not bool(getattr(rr, "_is_batching_updates", False)):
                                _check_nested_update_depth(rr)
                            dirty_mount.clear()
                            continue
                        if rr.pending_updates:
                            if not bool(getattr(rr, "_is_batching_updates", False)):
                                try:
                                    _check_nested_update_depth(rr)
                                except RuntimeError as err:
                                    if "Maximum update depth exceeded" in str(err):
                                        from .error_reporting import report_uncaught_error

                                        report_uncaught_error(self.container, err)
                                        next_v = []
                                        break
                                    raise
                            continue
                        break
                    new_ids = {id(x) for x in portal_targets}
                    for host in prev_portals:
                        if id(host) not in new_ids and hasattr(host, "root"):
                            host.root.children.clear()
                    _run_dom_class_gsbu_before_commit(self)
                    _commit_children(
                        container=self.container,
                        parent=self.container.root,
                        next_children=next_v,
                        path=[],
                        owner_stack="",
                    )
                    dirty_post = getattr(self.container, "_ryact_dom_mount_dirty", None)
                    if not isinstance(dirty_post, list) or not dirty_post:
                        break
                    if not bool(getattr(rr, "_is_batching_updates", False)):
                        _check_nested_update_depth(rr)
                    dirty_post.clear()
                else:
                    rr.pending_updates.clear()
                    raise RuntimeError(
                        "Maximum update depth exceeded. This can happen when a component repeatedly "
                        "calls setState inside componentWillUpdate or componentDidUpdate. React limits "
                        "the number of nested updates to prevent infinite loops."
                    )
            finally:
                self.container._ryact_dom_in_full_commit = False  # type: ignore[attr-defined]
            pending_bubbles = getattr(self.container, "_ryact_pending_portal_bubbles", None)
            if isinstance(pending_bubbles, list):
                for portal_target, bubble_path in pending_bubbles:
                    bubble_parent = (
                        _lookup_host_element_at_path(self.container, bubble_path)
                        if bubble_path
                        else self.container.root
                    )
                    if bubble_parent is None:
                        bubble_parent = self.container.root
                    _link_portal_event_bubble(portal_target, bubble_parent)
                pending_bubbles.clear()
            stack = getattr(self.container, "_ryact_commit_class_stack", None)
            if isinstance(stack, list) and stack:
                stack.pop()
            _ensure_class_instances_mounted(self)
            for _ in range(_NESTED_UPDATE_LIMIT + 1):
                if not getattr(self.container, "_ryact_dom_lifecycle_recommit", False):
                    break
                self.container._ryact_dom_lifecycle_recommit = False  # type: ignore[attr-defined]
                portal_targets_lc: list[Any] = list(self._portal_targets or [])
                next_v_lc = _render_to_virtual(
                    payload,
                    portal_targets=portal_targets_lc,
                    container=self.container,
                    parent_host_tag=None,
                    host_parent_path=(),
                    next_child_index=[0],
                )
                _commit_children(
                    container=self.container,
                    parent=self.container.root,
                    next_children=next_v_lc,
                    path=[],
                    owner_stack="",
                )
                _ensure_class_instances_mounted(self)
            else:
                self._reconciler_root.pending_updates.clear()
                raise RuntimeError(
                    "Maximum update depth exceeded. This can happen when a component repeatedly "
                    "calls setState inside componentWillUpdate or componentDidUpdate. React limits "
                    "the number of nested updates to prevent infinite loops."
                )
            for _ in range(_NESTED_UPDATE_LIMIT + 1):
                _flush_dom_layout_effects(self.container)
                rr_local = self._reconciler_root
                dirty_layout = getattr(self.container, "_ryact_dom_mount_dirty", None)
                has_dirty = isinstance(dirty_layout, list) and bool(dirty_layout)
                if not rr_local.pending_updates and not has_dirty:
                    break
                if not bool(getattr(rr_local, "_is_batching_updates", False)):
                    from ryact.reconciler import _check_nested_update_depth

                    _check_nested_update_depth(rr_local)
                if has_dirty and isinstance(dirty_layout, list):
                    dirty_layout.clear()
            else:
                self._reconciler_root.pending_updates.clear()
                raise RuntimeError(
                    "Maximum update depth exceeded. This can happen when a component repeatedly "
                    "calls setState inside componentWillUpdate or componentDidUpdate. React limits "
                    "the number of nested updates to prevent infinite loops."
                )
            _flush_dom_passive_effects(self.container)
            _dom_flush_deferred_boundary_errors(self.container)
            self._portal_targets = portal_targets
            if preserved_radio_checked:
                from .input_host import sync_radio_group_checked

                for name, value, _ in preserved_radio_checked:
                    for inp in self.container.query_selector_all("input"):
                        if (
                            str(inp.props.get("type", "")).lower() == "radio"
                            and inp.props.get("name") == name
                            and inp.props.get("value") == value
                        ):
                            inp._input_checked_dom = True
                            sync_radio_group_checked(inp, checked=True)
                            break
                self._hydrating = False
            self._has_committed = True
            self._last_commit_empty_hosts = len(self.container.root.children) == 0  # type: ignore[attr-defined]
            restore_preserved_focus_in_container(self.container)
            from .legacy_mount import _invoke_legacy_callback

            _invoke_legacy_callback(self)

        from ryact.concurrent import current_update_lane

        rr = self._reconciler_root
        bind_commit(rr, commit)
        effective_lane = current_update_lane() or lane
        schedule_update_on_root(rr, Update(lane=effective_lane, payload=element))
        self.container._ryact_dom_user_commit = True  # type: ignore[attr-defined]
        try:
            if rr.scheduler is None:
                try:
                    perform_work(rr, commit)
                except RuntimeError as err:
                    if "Maximum update depth exceeded" in str(err):
                        _clear_root_after_nested_depth_failure(self)
                    raise
        finally:
            self.container._ryact_dom_user_commit = False  # type: ignore[attr-defined]
            _root_render_depth -= 1


def _clear_root_after_nested_depth_failure(root: Root) -> None:
    from .dom_internals import clear_component_dom_node

    for inst in list(root._class_instances.values()):
        clear_component_dom_node(inst)
    root._class_instances.clear()
    dirty = getattr(root.container, "_ryact_dom_mount_dirty", None)
    if isinstance(dirty, list):
        dirty.clear()


def create_root(
    container: Any,
    options: Any = None,
    *,
    scheduler: Optional[Scheduler] = None,
) -> Root:
    if isinstance(container, Element):
        warn_create_root_jsx_element()
        raise TypeError("Target container is not a DOM element.")
    if not isinstance(container, Container):
        raise TypeError("Target container is not a DOM element.")
    if isinstance(options, Element):
        warn_create_root_jsx_element()
    if getattr(container, "_is_document_body", False):
        warn_create_root_on_document_body()
    identifier_prefix = ""
    if isinstance(options, dict):
        raw = options.get("identifierPrefix")
        if raw is not None:
            identifier_prefix = str(raw)
    root = Root(
        container=container,
        _reconciler_root=create_reconciler_root(container, scheduler=scheduler),
        _next_use_id=make_use_id_allocator(identifier_prefix=identifier_prefix),
    )
    container._ryact_dom_root = root
    register_modern_root(container, root)
    register_root_for_container(container, root)
    return root


def hydrate_root(
    container: Container,
    element: Element | None = None,
    *,
    scheduler: Optional[Scheduler] = None,
    on_recoverable_error: Callable[[Exception], None] | None = None,
) -> Root:
    if element is None:
        warn_hydrate_root_missing_children()
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
        ex_class = existing.props.get("class") or existing.props.get("className")
        nx_class = next0.props.get("class") or next0.props.get("className")
        if ex_class != nx_class:
            raise ValueError(f"Hydration mismatch: class {ex_class!r} != {nx_class!r}")
        # Compare first text child if both have one.
        ex_text = existing.children[0] if existing.children else None
        nx_text = next0.children[0] if next0.children else None
        if isinstance(ex_text, TextNode) and isinstance(nx_text, TextNode) and ex_text.text != nx_text.text:
            raise ValueError(f"Hydration mismatch: text {ex_text.text!r} != {nx_text.text!r}")
    elif existing is not None or next0 is not None:
        raise ValueError("Hydration mismatch: existing and next trees differ")
