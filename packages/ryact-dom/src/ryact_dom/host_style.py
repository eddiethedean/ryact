"""Client-side ``CSSStyleDeclaration`` subset for host nodes (ReactDOMComponent style parity)."""
from __future__ import annotations

import math
import warnings
from typing import Any

from ryact.dev import is_dev

# Keep in sync with server._UNITLESS_NUMBER_PROPS (React DOMPropertyOperations / CSSPropertyOperations).
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
        "fontSize",
        "margin",
        "marginTop",
        "marginBottom",
        "marginLeft",
        "marginRight",
        "padding",
        "paddingTop",
        "paddingBottom",
        "paddingLeft",
        "paddingRight",
    }
)


def client_style_property_value(prop: str, value: Any) -> str:
    """Assign a single style property on the host (empty string clears)."""

    if value is None or value is False:
        return ""
    if isinstance(value, bool):
        return ""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
            if is_dev():
                warnings.warn(
                    f"`NaN` is an invalid value for the `{prop}` css style property.\n"
                    f"    in element",
                    UserWarning,
                    stacklevel=6,
                )
            return ""
        if prop.startswith("--"):
            return str(value)
        if prop in _UNITLESS_NUMBER_PROPS:
            return str(value)
        return f"{value}px"
    s = str(value).strip()
    return s if s else ""


def sync_host_style_from_props(host: Any) -> None:
    """Rebuild ``host._host_style`` from ``host.props['style']`` (full replace semantics)."""

    from .dom import ElementNode

    if not isinstance(host, ElementNode):
        return
    style = host.props.get("style")
    if not isinstance(style, dict):
        host._host_style.clear()
        return
    next_keys: dict[str, str] = {}
    for k, v in style.items():
        prop = str(k)
        next_keys[prop] = client_style_property_value(prop, v)
    for k in list(host._host_style.keys()):
        if k not in next_keys:
            host._host_style[k] = ""
    host._host_style.update(next_keys)


class HostStyleDeclaration:
    """DOM-like ``element.style`` for translated ReactDOMComponent tests."""

    def __init__(self, owner: Any) -> None:
        object.__setattr__(self, "_owner", owner)

    def _store(self) -> dict[str, str]:
        return self._owner._host_style

    def __getattr__(self, name: str) -> str:
        if name.startswith("_"):
            raise AttributeError(name)
        return self._store().get(name, "")

    def __setattr__(self, name: str, value: Any) -> None:
        if name == "_owner":
            object.__setattr__(self, name, value)
            return
        self._store()[name] = "" if value is None else str(value)
