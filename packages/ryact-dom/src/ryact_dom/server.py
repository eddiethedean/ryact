from __future__ import annotations

import math
import warnings
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any

from ryact.dev import is_dev
from ryact.element import Element, coerce_top_level_render_result, props_for_component_render
from ryact.hooks import _render_component, sync_external_store_server_reads

from ._version_check import check_versions as _check_versions
from .html_props import (
    _is_custom_element_dom_tag,
    dom_event_type_for_listener_key,
    html_attribute_name,
    is_boolean_html_attribute,
    normalize_host_prop_dict,
    warn_intrinsic_html_tag_casing_dev,
)
from .intrinsic_tag_dev import format_dangerously_inner_html_value_dev, warn_unrecognized_host_tag_dev
from .mount_validation import prepare_host_mount_props, void_element_children_or_innerhtml_error
from .select_binding import process_select_element_children, strip_select_internal_props
from .svg_namespace import SVG_NAMESPACE, is_svg_host_tag, serialize_xlink_href_attr
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

_check_versions()

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
        # ReactDOM treats menuitem as void-ish, but historically emits a closing tag in markup.
        "menuitem",
    }
)

_ssr_component_stack: list[str] = []
_ssr_render_depth: int = 0


class _SsrStackFrame:
    def __init__(self, name: str) -> None:
        self._name = name

    def __enter__(self) -> None:
        _ssr_component_stack.append(self._name)

    def __exit__(self, exc_type, exc, tb) -> bool | None:
        if _ssr_component_stack and _ssr_component_stack[-1] == self._name:
            _ssr_component_stack.pop()
        return None


def _ssr_stack_str() -> str:
    from ryact.devtools import format_component_stack

    return format_component_stack(list(_ssr_component_stack))


def render_to_string(
    element: Any,
    *,
    dom_nesting_mount_tag: str | None = None,
    identifier_prefix: str = "",
) -> str:
    """
    Very early server-rendering placeholder.

    The long-term parity target is `react-dom/server` semantics, but this provides
    a deterministic baseline for upcoming translated tests.
    """

    global _ssr_render_depth
    if is_dev() and _ssr_render_depth > 0:
        warnings.warn(
            "renderToString was called while already rendering. "
            "Fix your code so you are not calling renderToString from inside another renderToString.",
            UserWarning,
            stacklevel=2,
        )
    _ssr_render_depth += 1
    parts: list[str] = []
    mount_ctx = (
        SimpleNamespace(dom_nesting_mount_tag=dom_nesting_mount_tag)
        if dom_nesting_mount_tag is not None
        else None
    )
    ancestor_info = initial_ancestor_info_dev(mount_ctx)
    next_id = make_use_id_allocator(identifier_prefix=identifier_prefix)
    try:
        with sync_external_store_server_reads():
            if is_dev() and isinstance(element, (str, int, float)):
                validate_text_nesting_dev(
                    text=str(element),
                    ancestor_info=ancestor_info,
                    component_stack=_ssr_stack_str(),
                )
            _render(
                element,
                parts,
                parent_host_tag=None,
                ancestor_info=ancestor_info,
                next_id=next_id,
            )
        return "".join(parts)
    finally:
        _ssr_render_depth -= 1


@dataclass
class PipeableStream:
    _html: str
    _on_shell_ready: Callable[[], None] | None
    _on_all_ready: Callable[[], None] | None
    _on_error: Callable[[Exception], None] | None
    _aborted: bool = False

    def pipe(self, write: Callable[[str], None]) -> None:
        if self._aborted:
            return
        try:
            if self._on_shell_ready is not None:
                self._on_shell_ready()
            write(self._html)
            if self._on_all_ready is not None:
                self._on_all_ready()
        except Exception as err:  # pragma: no cover
            if self._on_error is not None:
                self._on_error(err)
            raise

    def abort(self, reason: Exception | None = None) -> None:
        self._aborted = True
        if reason is not None and self._on_error is not None:
            self._on_error(reason)


def render_to_pipeable_stream(
    element: Any,
    *,
    on_shell_ready: Callable[[], None] | None = None,
    on_all_ready: Callable[[], None] | None = None,
    on_error: Callable[[Exception], None] | None = None,
    dom_nesting_mount_tag: str | None = None,
) -> PipeableStream:
    # Minimal streaming slice: compute full HTML eagerly, but expose a pipeable interface.
    html = render_to_string(element, dom_nesting_mount_tag=dom_nesting_mount_tag)
    return PipeableStream(
        _html=html,
        _on_shell_ready=on_shell_ready,
        _on_all_ready=on_all_ready,
        _on_error=on_error,
    )


def _escape_attr_value(value: object) -> str:
    """Escape attribute values like React's ``quoteAttributeValueForBrowser`` (SSR subset)."""

    s = str(value)
    s = s.replace("&", "&amp;")
    s = s.replace('"', "&quot;")
    s = s.replace("'", "&#x27;")
    s = s.replace("<", "&lt;")
    s = s.replace(">", "&gt;")
    return s


def _escape_text_node(value: object) -> str:
    """Escape text nodes like React's ``escapeTextForBrowser`` (SSR subset)."""

    s = str(value)
    s = s.replace("&", "&amp;")
    s = s.replace("<", "&lt;")
    s = s.replace(">", "&gt;")
    s = s.replace('"', "&quot;")
    s = s.replace("'", "&#x27;")
    return s


def _serialize_opening_tag_attrs(props_norm: dict[str, Any], *, tag: str | None = None) -> str:
    parts: list[str] = []
    for k, v in props_norm.items():
        if k == "children":
            continue
        if tag is not None and tag.lower() == "textarea" and k in (
            "value",
            "defaultValue",
            "default_value",
        ):
            continue
        if k == "style" and isinstance(v, dict):
            css = _serialize_style_dict(v)
            if css:
                parts.append(f' style="{_escape_attr_value(css)}"')
            continue
        if k in (
            "dangerouslySetInnerHTML",
            "dangerously_set_inner_html",
            "suppressContentEditableWarning",
            "suppress_content_editable_warning",
        ):
            continue
        if callable(v) and dom_event_type_for_listener_key(k) is not None:
            continue
        if callable(v):
            # Custom element property assignments (not HTML attributes); React omits from markup.
            continue
        an = html_attribute_name(k)
        if (
            isinstance(v, bool)
            and tag is not None
            and _is_custom_element_dom_tag(tag)
            and not is_boolean_html_attribute(k)
        ):
            if v is True:
                parts.append(f' {an}=""')
            continue
        if is_boolean_html_attribute(k):
            if v is True:
                parts.append(f" {an}")
            # False / None: omit (matches common React DOM string output for booleans).
            continue
        if v is None:
            continue
        parts.append(f' {an}="{_escape_attr_value(v)}"')
    return "".join(parts)


_UNITLESS_NUMBER_PROPS: frozenset[str] = frozenset(
    {
        "animationIterationCount",
        "aspectRatio",
        "borderImageOutset",
        "borderImageSlice",
        "borderImageWidth",
        "boxFlex",
        "boxFlexGroup",
        "boxOrdinalGroup",
        "columnCount",
        "columns",
        "flex",
        "flexGrow",
        "flexPositive",
        "flexShrink",
        "flexNegative",
        "flexOrder",
        "fontWeight",
        "gridArea",
        "gridRow",
        "gridRowEnd",
        "gridRowSpan",
        "gridRowStart",
        "gridColumn",
        "gridColumnEnd",
        "gridColumnSpan",
        "gridColumnStart",
        "lineClamp",
        "lineHeight",
        "opacity",
        "order",
        "orphans",
        "scale",
        "tabSize",
        "widows",
        "zIndex",
        "zoom",
    }
)


def _hyphenate_style_name(name: str) -> str:
    if name.startswith("--"):
        return name
    # Warn for hyphenated style names; prefer camelCase.
    if "-" in name:
        warnings.warn(
            f"Unsupported style property {name!r}. Did you mean {name.replace('-', '')!r}?",
            UserWarning,
            stacklevel=4,
        )
        return name
    # Warn on mis-capitalized vendor prefixes like webkitTransform.
    if (
        name.startswith("webkit")
        or name.startswith("moz")
        or (name.startswith("o") and len(name) > 1 and name[1].isupper())
    ):
        warnings.warn(
            f"Unsupported vendor-prefixed style property {name!r}. Did you mean {name[:1].upper() + name[1:]!r}?",
            UserWarning,
            stacklevel=4,
        )
    if name.startswith("ms") and not name.startswith("ms-"):
        # React expects ms* in camelCase (msTransition) to serialize as -ms-transition.
        pass

    out: list[str] = []
    for i, ch in enumerate(name):
        if ch.isupper():
            if i == 0:
                out.append("-")
            out.append("-")
            out.append(ch.lower())
        else:
            out.append(ch)
    s = "".join(out).replace("--", "-")
    # Normalize leading vendor prefix.
    if s.startswith("ms-"):
        s = "-ms-" + s[3:]
    if s.startswith("webkit-"):
        s = "-webkit-" + s[7:]
    if s.startswith("moz-"):
        s = "-moz-" + s[4:]
    if s.startswith("o-"):
        s = "-o-" + s[2:]
    return s


def _serialize_style_value(prop: str, value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
            warnings.warn(
                f"`{prop}` style value is invalid: {value!r}.",
                UserWarning,
                stacklevel=4,
            )
            return None
        if prop.startswith("--"):
            return str(value)
        if prop in _UNITLESS_NUMBER_PROPS:
            return str(value)
        return f"{value}px"
    s = str(value).strip()
    if s.endswith(";"):
        warnings.warn(
            f"Style property values shouldn't contain a trailing semicolon. Try {s[:-1]!r} instead.",
            UserWarning,
            stacklevel=4,
        )
        s = s[:-1]
    return s if s else None


def _serialize_style_dict(style: dict[str, Any]) -> str:
    if not style:
        return ""
    parts: list[str] = []
    for k, v in style.items():
        if v is None:
            continue
        name = _hyphenate_style_name(str(k))
        val = _serialize_style_value(str(k), v)
        if val is None:
            continue
        parts.append(f"{name}:{val}")
    return ";".join(parts)


def _render(
    node: Any,
    out: list[str],
    *,
    parent_host_tag: str | None,
    ancestor_info: AncestorInfoDev | None = None,
    next_id: Callable[[], str] | None = None,
) -> None:
    if node is None:
        return
    if ancestor_info is None:
        ancestor_info = initial_ancestor_info_dev(None)
    if isinstance(node, (str, int, float)):
        out.append(_escape_text_node(node))
        return
    if isinstance(node, dict):
        keys = ", ".join(repr(k) for k in node.keys())
        raise TypeError(
            f"Objects are not valid as a React child (found: object with keys {{{keys}}}). "
            "If you meant to render a collection of children, use an array instead."
        )
    if isinstance(node, Element) and isinstance(node.type, str):
        # Wrapper/sentinel types used by the core/noop reconciler.
        if node.type == "__fragment__":
            for c in node.props.get("children", ()):
                _render(
                    c,
                    out,
                    parent_host_tag=parent_host_tag,
                    ancestor_info=ancestor_info,
                    next_id=next_id,
                )
            return
        if node.type == "__strict_mode__":
            children = node.props.get("children", ())
            child = children[0] if children else None
            _render(
                child,
                out,
                parent_host_tag=parent_host_tag,
                ancestor_info=ancestor_info,
                next_id=next_id,
            )
            return
        if node.type == "__portal__":
            for c in node.props.get("children", ()):
                _render(
                    c,
                    out,
                    parent_host_tag=parent_host_tag,
                    ancestor_info=ancestor_info,
                    next_id=next_id,
                )
            return
        if node.type == "__suspense__":
            # Early server placeholder: render children directly.
            for c in node.props.get("children", ()):
                _render(
                    c,
                    out,
                    parent_host_tag=parent_host_tag,
                    ancestor_info=ancestor_info,
                    next_id=next_id,
                )
            return
        if node.type == "__offscreen__":
            mode = node.props.get("mode") if isinstance(node.props, Mapping) else None
            if mode == "hidden":
                return
            for c in node.props.get("children", ()):
                _render(
                    c,
                    out,
                    parent_host_tag=parent_host_tag,
                    ancestor_info=ancestor_info,
                    next_id=next_id,
                )
            return

        validate_host_intrinsic_tag_name(node.type)
        if is_dev():
            warn_intrinsic_html_tag_casing_dev(node.type, parent_host_tag)
            warn_unrecognized_host_tag_dev(node.type, parent_host_tag)
        tag_l = node.type.lower()
        if is_dev():
            validate_dom_nesting_host_child_dev(
                child_tag=tag_l,
                ancestor_info=ancestor_info,
                component_stack=_ssr_stack_str(),
            )
        info_inside = updated_ancestor_info_dev(ancestor_info, tag_l)
        props_norm = normalize_host_prop_dict(
            prepare_host_mount_props(node.props, tag=node.type),
            tag=node.type,
            is_ssr=True,
        )
        dsh = props_norm.get("dangerouslySetInnerHTML") or props_norm.get("dangerously_set_inner_html")
        raw_children = node.props.get("children", ())
        if isinstance(dsh, dict) and dsh.get("__html") is not None and raw_children:
            raise ValueError("Can only set one of `children` or `props.dangerouslySetInnerHTML`.")
        if tag_l == "select":
            raw_map = dict(node.props) if isinstance(node.props, Mapping) else {}
            raw_children = process_select_element_children(raw_map, props_norm, raw_children)
            strip_select_internal_props(props_norm, for_ssr=True)
        elif tag_l == "textarea":
            raw_map = dict(node.props) if isinstance(node.props, Mapping) else {}
            ta = process_textarea_element_children(raw_map, props_norm, raw_children)
            raw_children = ta.children
            strip_textarea_internal_props(props_norm, for_ssr=True)
        out.append("<" + node.type)
        if tag_l == "svg" and not (
            parent_host_tag is not None and is_svg_host_tag(parent_host_tag.lower())
        ):
            out.append(f' xmlns="{SVG_NAMESPACE}"')
        xlink = serialize_xlink_href_attr(props_norm)
        if xlink:
            out.append(xlink)
        out.append(_serialize_opening_tag_attrs(props_norm, tag=node.type))
        if tag_l in _VOID_TAGS and tag_l != "menuitem":
            if isinstance(dsh, dict) and dsh.get("__html") is not None:
                raise void_element_children_or_innerhtml_error(node.type)
            if node.props.get("children", ()):
                raise void_element_children_or_innerhtml_error(node.type)
            if node.type != tag_l:
                out.append("></" + node.type + ">")
            else:
                out.append("/>")
            return
        out.append(">")
        if isinstance(dsh, dict) and dsh.get("__html") is not None:
            # Match the "dangerously" contract: inject raw HTML string without escaping.
            out.append(format_dangerously_inner_html_value_dev(dsh.get("__html")))
        else:
            for c in raw_children:
                if is_dev() and isinstance(c, (str, int, float)):
                    validate_text_nesting_dev(
                        text=str(c),
                        ancestor_info=info_inside,
                        component_stack=_ssr_stack_str(),
                    )
                _render(
                    c,
                    out,
                    parent_host_tag=node.type,
                    ancestor_info=info_inside,
                    next_id=next_id,
                )
        out.append("</" + node.type + ">")
        return
    if isinstance(node, Element) and callable(node.type):
        name = getattr(node.type, "__name__", "Anonymous")
        with _SsrStackFrame(name):
            # Fresh hook list per component instance (not keyed by function identity).
            rendered = coerce_top_level_render_result(
                _render_component(
                    node.type,
                    dict(props_for_component_render(node.type, node.props)),
                    [],
                    next_id=next_id,
                )
            )
            _render(
                rendered,
                out,
                parent_host_tag=parent_host_tag,
                ancestor_info=ancestor_info,
                next_id=next_id,
            )
        return
    raise TypeError(f"Unsupported node for server rendering: {type(node)!r}")
