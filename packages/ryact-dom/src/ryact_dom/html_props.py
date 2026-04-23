from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def _merge_class_values(*values: Any) -> str:
    parts: list[str] = []
    for v in values:
        if v is None or v == "":
            continue
        parts.append(str(v))
    return " ".join(parts)


def normalize_host_prop_dict(props: Mapping[str, Any]) -> dict[str, Any]:
    """
    Normalize React- and Python-style host props to a single DOM-facing shape.

    - ``className`` / ``class_name`` / ``class`` → ``class`` (merged).
    """
    out = dict(props)
    classes: list[Any] = []
    for key in ("class", "className", "class_name"):
        if key in out:
            classes.append(out.pop(key))
    if classes:
        out["class"] = _merge_class_values(*classes)
    return out


def dom_event_type_for_listener_key(prop: str) -> str | None:
    """
    Map a prop name to a DOM event type, or None if this is not an event prop.

    Accepts React-style ``onClick`` and Pythonic ``on_click`` / ``on_key_down``.
    """
    if prop.startswith("on_") and len(prop) > 3:
        return prop[3:].replace("_", "")
    if prop.startswith("on") and len(prop) > 2:
        return prop[2:].lower()
    return None


def is_event_listener_prop(prop: str, value: Any) -> bool:
    return callable(value) and dom_event_type_for_listener_key(prop) is not None


def html_attribute_name(prop_key: str) -> str:
    """``data_foo`` → ``data-foo`` (common Pythonic spelling for data attributes)."""
    if prop_key.startswith("data_") and len(prop_key) > 5:
        return "data-" + prop_key[5:].replace("_", "-")
    return prop_key
