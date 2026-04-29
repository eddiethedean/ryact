from __future__ import annotations

import math
import re
import warnings
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Callable

from ryact.element import Element, coerce_top_level_render_result, props_for_component_render
from ryact.hooks import _render_component

from .html_props import (
    dom_event_type_for_listener_key,
    html_attribute_name,
    is_boolean_html_attribute,
    normalize_host_prop_dict,
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
        # ReactDOM treats menuitem as void-ish, but historically emits a closing tag in markup.
        "menuitem",
    }
)


def render_to_string(element: Any) -> str:
    """
    Very early server-rendering placeholder.

    The long-term parity target is `react-dom/server` semantics, but this provides
    a deterministic baseline for upcoming translated tests.
    """

    parts: list[str] = []
    _render(element, parts)
    return "".join(parts)


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
) -> PipeableStream:
    # Minimal streaming slice: compute full HTML eagerly, but expose a pipeable interface.
    html = render_to_string(element)
    return PipeableStream(
        _html=html,
        _on_shell_ready=on_shell_ready,
        _on_all_ready=on_all_ready,
        _on_error=on_error,
    )


_hooks_by_component = {}  # type: dict[int, list[Any]]


def _get_component_hooks(component: Any) -> list[Any]:
    cid = id(component)
    if cid not in _hooks_by_component:
        _hooks_by_component[cid] = []
    return _hooks_by_component[cid]


_VALID_TAG_RE = re.compile(r"^[A-Za-z][A-Za-z0-9:_-]*$")


def _escape_attr_value(value: object) -> str:
    s = str(value)
    return s.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;")


def _escape_text_node(value: object) -> str:
    s = str(value)
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _serialize_opening_tag_attrs(props_norm: dict[str, Any]) -> str:
    parts: list[str] = []
    for k, v in props_norm.items():
        if k == "children":
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
    if name.startswith("webkit") or name.startswith("moz") or (
        name.startswith("o") and len(name) > 1 and name[1].isupper()
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


def _validate_tag_name(tag: str) -> None:
    # Minimal server-side tag sanitization slice: reject obvious injection/invalid tags.
    if not _VALID_TAG_RE.match(tag):
        raise ValueError(f"Invalid tag name: {tag!r}")
    lowered = tag.lower()
    if lowered.startswith("script") and "<" in lowered:
        raise ValueError(f"Invalid tag name: {tag!r}")


def _render(node: Any, out: list[str]) -> None:
    if node is None:
        return
    if isinstance(node, (str, int, float)):
        out.append(_escape_text_node(node))
        return
    if isinstance(node, Element) and isinstance(node.type, str):
        # Wrapper/sentinel types used by the core/noop reconciler.
        if node.type == "__fragment__":
            for c in node.props.get("children", ()):
                _render(c, out)
            return
        if node.type == "__strict_mode__":
            children = node.props.get("children", ())
            child = children[0] if children else None
            _render(child, out)
            return
        if node.type == "__portal__":
            for c in node.props.get("children", ()):
                _render(c, out)
            return
        if node.type == "__suspense__":
            # Early server placeholder: render children directly.
            for c in node.props.get("children", ()):
                _render(c, out)
            return
        if node.type == "__offscreen__":
            mode = node.props.get("mode") if isinstance(node.props, Mapping) else None
            if mode == "hidden":
                return
            for c in node.props.get("children", ()):
                _render(c, out)
            return

        _validate_tag_name(node.type)
        tag_l = node.type.lower()
        out.append("<" + node.type)
        props_norm = normalize_host_prop_dict(node.props, tag=node.type)
        out.append(_serialize_opening_tag_attrs(props_norm))
        out.append(">")
        dsh = props_norm.get("dangerouslySetInnerHTML") or props_norm.get(
            "dangerously_set_inner_html"
        )
        if tag_l in _VOID_TAGS and tag_l != "menuitem":
            if isinstance(dsh, dict) and dsh.get("__html") is not None:
                raise ValueError(
                    f"{node.type} is a void element tag and must not have `dangerouslySetInnerHTML`."
                )
            if node.props.get("children", ()):
                raise ValueError(
                    f"{node.type} is a void element tag and must not have `children`."
                )
            # Still emit opening+closing tag for now (ryact-dom SSR placeholder).
            out.append("</" + node.type + ">")
            return
        if isinstance(dsh, dict) and dsh.get("__html") is not None:
            # Match the "dangerously" contract: inject raw HTML string without escaping.
            out.append(str(dsh.get("__html")))
        else:
            for c in node.props.get("children", ()):
                _render(c, out)
        out.append("</" + node.type + ">")
        return
    if isinstance(node, Element) and callable(node.type):
        rendered = coerce_top_level_render_result(
            _render_component(
                node.type,
                dict(props_for_component_render(node.type, node.props)),
                _get_component_hooks(node.type),
            )
        )
        _render(rendered, out)
        return
    raise TypeError(f"Unsupported node for server rendering: {type(node)!r}")
