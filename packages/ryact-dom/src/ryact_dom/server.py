from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Callable

from ryact.element import Element, coerce_top_level_render_result
from ryact.hooks import _render_component

from .html_props import (
    dom_event_type_for_listener_key,
    html_attribute_name,
    is_boolean_html_attribute,
    normalize_host_prop_dict,
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
            mode = node.props.get("mode") if isinstance(node.props, dict) else None
            if mode == "hidden":
                return
            for c in node.props.get("children", ()):
                _render(c, out)
            return

        _validate_tag_name(node.type)
        out.append("<" + node.type)
        props_norm = normalize_host_prop_dict(node.props, tag=node.type)
        out.append(_serialize_opening_tag_attrs(props_norm))
        out.append(">")
        for c in node.props.get("children", ()):
            _render(c, out)
        out.append("</" + node.type + ">")
        return
    if isinstance(node, Element) and callable(node.type):
        rendered = coerce_top_level_render_result(
            _render_component(node.type, dict(node.props), _get_component_hooks(node.type))
        )
        _render(rendered, out)
        return
    raise TypeError(f"Unsupported node for server rendering: {type(node)!r}")
