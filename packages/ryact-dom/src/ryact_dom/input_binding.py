"""``<input>`` value coercion helpers (ReactDOMInput parity with textarea)."""
from __future__ import annotations

import warnings
from collections.abc import Mapping
from typing import Any

from ryact.dev import is_dev
from ryact.element import UNDEFINED

from .textarea_binding import _invalid_textarea_host_value, _textarea_stringify


def _prop_present(raw: Mapping[str, Any], key: str) -> bool:
    if key not in raw:
        return False
    return raw[key] is not UNDEFINED


def input_host_default_from_raw(raw: Mapping[str, Any]) -> str | None:
    """Latest ``defaultValue`` for the host ``defaultValue`` property (``''`` when omitted)."""

    if not _prop_present(raw, "defaultValue") and not _prop_present(raw, "default_value"):
        return ""
    dk = "defaultValue" if _prop_present(raw, "defaultValue") else "default_value"
    v = raw[dk]
    if v is None:
        return ""
    if _invalid_textarea_host_value(v):
        return ""
    return _textarea_stringify(v, prop="defaultValue", coerce_temporal=False)


def warn_and_coerce_invalid_input_value_props_inplace(props: dict[str, Any], *, tag: str) -> None:
    if tag.lower() != "input":
        return
    for k in ("value", "defaultValue", "default_value"):
        if k not in props:
            continue
        v = props[k]
        if not _invalid_textarea_host_value(v):
            continue
        if is_dev():
            warnings.warn(
                f"Invalid value for prop `{k}` on <input> tag. "
                "Either remove it from the element, or pass a string or number value to "
                "keep it in the DOM. For details, see https://react.dev/link/attribute-behavior \n"
                "    in input",
                UserWarning,
                stacklevel=5,
            )
        props[k] = ""


def preserve_value_on_invalid_form_field_inplace(
    raw: dict[str, Any],
    host_prev: Any,
) -> None:
    from .dom import ElementNode

    if not isinstance(host_prev, ElementNode) or host_prev.tag.lower() != "input":
        return
    if _prop_present(raw, "value"):
        return
    for dk in ("defaultValue", "default_value"):
        if dk not in raw:
            continue
        if _invalid_textarea_host_value(raw[dk]):
            raw["value"] = host_prev.dom_input_value()
        return


def coerce_input_value_prop_inplace(props: dict[str, Any], *, prop: str) -> None:
    """Coerce ``value`` / ``defaultValue`` including Temporal-like ``valueOf`` failures."""

    if prop not in props:
        return
    if _invalid_textarea_host_value(props[prop]):
        props[prop] = ""
        return
    try:
        props[prop] = _textarea_stringify(props[prop], prop=prop)
    except TypeError:
        raise
