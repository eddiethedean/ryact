"""``<option>`` host children flattening and value (ReactDOMOption parity)."""
from __future__ import annotations

import warnings
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from ryact.dev import is_dev
from ryact.element import UNDEFINED, Element

from .dom_dev_warnings import react_dev_in_suffix
from .select_binding import _invalid_option_host_value

def _prop_present(raw: Mapping[str, Any], key: str) -> bool:
    if key not in raw:
        return False
    return raw[key] is not UNDEFINED


def _option_stringify(v: Any) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if v is None:
        return ""
    return str(v)


def _is_elementish_child(c: object) -> bool:
    if isinstance(c, Element):
        return False
    if isinstance(c, (str, int, float, bool)):
        return False
    if isinstance(c, Mapping):
        sym = getattr(c, "$$typeof", None)
        if sym is not None and "element" in str(sym).lower():
            return True
        return hasattr(c, "props") and hasattr(c, "__str__")
    return hasattr(c, "__str__") and not isinstance(c, type)


def _text_from_elementish(c: object) -> str:
    if isinstance(c, Mapping):
        props = c.get("props")
        if isinstance(props, Mapping) and "content" in props:
            return str(props["content"])
    return str(c)


@dataclass(frozen=True)
class ProcessedOption:
    children: list[Any]
    host_value: str
    force_value_attr: bool


def _warn_option_dev(msg: str, *, owner_stack: str) -> None:
    if not is_dev():
        return
    suffix = react_dev_in_suffix(host_tag="option", owner_stack=owner_stack)
    warnings.warn(f"{msg}\n{suffix}", UserWarning, stacklevel=5)


def _flatten_rendered_text(nodes: list[Any], *, owner_stack: str) -> str:
    from .root import RenderedElement, RenderedText

    parts: list[str] = []
    for n in nodes:
        if isinstance(n, RenderedText):
            if n.text:
                parts.append(n.text)
            continue
        if isinstance(n, RenderedElement):
            tl = n.tag.lower()
            _warn_option_dev(
                f"In HTML, <{tl}> cannot be a child of <option>.\n"
                "This will cause a hydration error.",
                owner_stack=owner_stack,
            )
            parts.append(_flatten_rendered_children(n.children, owner_stack=owner_stack))
    return " ".join(parts)


def _flatten_rendered_children(nodes: list[Any], *, owner_stack: str) -> str:
    from .root import RenderedElement, RenderedText

    parts: list[str] = []
    for n in nodes:
        if isinstance(n, RenderedText):
            if n.text.strip():
                parts.append(n.text.strip())
        elif isinstance(n, RenderedElement):
            parts.append(_flatten_rendered_text([n], owner_stack=owner_stack))
    return " ".join(p for p in parts if p)


def _option_append_primitive(acc: str, s: str, *, last_was_rendered: bool) -> str:
    if not s:
        return acc
    need_space = bool(
        acc
        and not acc.endswith(" ")
        and (last_was_rendered or (acc[-1].isdigit() and s[0].isdigit()))
    )
    if need_space:
        acc += " "
    return acc + s


def flatten_option_label_in_order(
    visible_children: list[object],
    *,
    render_one: Callable[[object], list[Any]],
    owner_stack: str,
) -> tuple[str, bool]:
    """Preserve child order; space-separate rendered/component segments like React."""

    acc = ""
    last_was_rendered = False
    had_callable = False
    for ch in visible_children:
        if ch is True or ch is None or ch is False:
            continue
        if isinstance(ch, (str, int, float)):
            acc = _option_append_primitive(acc, str(ch), last_was_rendered=last_was_rendered)
            last_was_rendered = False
            continue
        if _is_elementish_child(ch):
            s = _text_from_elementish(ch)
            if acc and not acc.endswith(" "):
                acc += " "
            acc += s
            last_was_rendered = True
            continue
        if isinstance(ch, Element) and callable(ch.type) and not isinstance(ch.type, type):
            had_callable = True
        piece = _flatten_rendered_text(render_one(ch), owner_stack=owner_stack)
        if piece:
            if acc and not acc[-1].isspace():
                acc += " "
            acc += piece
            last_was_rendered = True
    return acc, had_callable


def process_option_children_after_render(
    *,
    raw: Mapping[str, Any],
    props: dict[str, Any],
    owner_stack: str,
    visible_children: list[object],
    flattened_text: str,
    had_callable_child: bool,
) -> ProcessedOption:
    """Flatten option children to one text node and compute host ``value``."""

    has_value = _prop_present(raw, "value")
    dsh = props.get("dangerouslySetInnerHTML") or props.get("dangerously_set_inner_html")
    if isinstance(dsh, Mapping) and dsh.get("__html") is not None:
        text = str(dsh.get("__html", ""))
        if is_dev() and not has_value:
            _warn_option_dev(
                "Pass a `value` prop if you set dangerouslyInnerHTML so React knows "
                "which value should be selected.",
                owner_stack=owner_stack,
            )
        host_value = _option_stringify(raw["value"]) if has_value else text
        from .root import RenderedText

        return ProcessedOption(
            children=[RenderedText(text=text)] if text else [],
            host_value=host_value,
            force_value_attr=True,
        )

    elementish_vals = [
        _text_from_elementish(ch)
        for ch in visible_children
        if ch is not True and ch is not None and ch is not False and _is_elementish_child(ch)
    ]

    if had_callable_child and not has_value:
        _warn_option_dev(
            "Cannot infer the option value of complex children. Pass a `value` prop "
            "or use a plain string as children to <option>.",
            owner_stack=owner_stack,
        )

    text = flattened_text
    if has_value:
        rv = raw["value"]
        if rv is None:
            host_value = text
            force_attr = True
        elif _invalid_option_host_value(rv):
            host_value = text
            force_attr = False
        else:
            host_value = _option_stringify(rv)
            force_attr = True
    elif elementish_vals:
        host_value = elementish_vals[-1]
        force_attr = True
    else:
        host_value = text
        force_attr = bool(text)

    if has_value and raw.get("value") == "":
        force_attr = True
        host_value = ""

    from .root import RenderedText

    return ProcessedOption(
        children=[RenderedText(text=text)] if text else [],
        host_value=host_value,
        force_value_attr=force_attr,
    )


def strip_option_internal_props(props: dict[str, Any]) -> None:
    props.pop("dangerouslySetInnerHTML", None)
    props.pop("dangerously_set_inner_html", None)


def init_option_host_on_mount(node: Any) -> None:
    from .dom import ElementNode, TextNode

    if not isinstance(node, ElementNode) or node.tag.lower() != "option":
        return
    text = ""
    if node.children and isinstance(node.children[0], TextNode):
        text = node.children[0].text
    if "value" in node.props:
        pv = node.props["value"]
        if pv is None:
            node._option_value_attr = text
            node._option_force_value_attr = True
        elif _invalid_option_host_value(pv):
            node._option_value_attr = text
            node._option_force_value_attr = False
        else:
            node._option_value_attr = _option_stringify(pv)
            node._option_force_value_attr = True
    elif getattr(node, "_option_force_value_attr", False):
        node._option_value_attr = ""
    elif text:
        node._option_value_attr = text
        node._option_force_value_attr = False
    else:
        node._option_value_attr = None
        node._option_force_value_attr = False


def sync_option_host_after_props_update(node: Any, *, prev_props: Mapping[str, Any]) -> None:
    init_option_host_on_mount(node)
