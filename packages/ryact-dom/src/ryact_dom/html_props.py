from __future__ import annotations

import warnings
from collections.abc import Mapping
from typing import Any

from ryact.dev import is_dev


def _merge_class_values(*values: Any) -> str:
    parts: list[str] = []
    for v in values:
        if v is None or v == "":
            continue
        parts.append(str(v))
    return " ".join(parts)


def normalize_host_prop_dict(
    props: Mapping[str, Any],
    *,
    tag: str | None = None,
) -> dict[str, Any]:
    """
    Normalize React- and Python-style host props to a single DOM-facing shape.

    - ``className`` / ``class_name`` / ``class`` → ``class`` (merged).
    - Explicit ``None`` / empty clears to ``class=""`` when any class key was present
      (matches DOMPropertyOperations: empty string instead of omitting the attribute).
    - Empty ``href`` is omitted for most tags, but preserved for ``<a>`` (updateDOM empty
      href on anchors) when ``tag`` is ``"a"``. Empty ``src`` is still omitted.
    - Boolean values on non-boolean DOM attributes (custom ``whatever``, etc.) are dropped
      so they are not stringified as ``"True"`` / ``"False"`` (ReactDOMComponent parity).
    - Non-listener callables on custom attributes are dropped (invalid attribute values).
    - Plain ``dict`` values (except ``style`` / ``dangerouslySetInnerHTML``) stringify like
      browser ``String(object)`` for generic custom attributes.
    - Known DOM props with bad casing (e.g. ``SiZe``) are renamed to canonical keys; DEV warns.
    - ``float('nan')`` attribute values stringify to ``\"NaN\"``; DEV warns like ReactDOM.
    """
    out = dict(props)
    had_class_key = any(k in out for k in ("class", "className", "class_name"))
    classes: list[Any] = []
    for key in ("class", "className", "class_name"):
        if key in out:
            classes.append(out.pop(key))
    if classes:
        merged = _merge_class_values(*classes)
        if merged:
            out["class"] = merged
        elif had_class_key:
            out["class"] = ""
    _normalize_dom_property_key_casing_inplace(out)
    for k in list(out.keys()):
        if k == "children":
            continue
        v = out[k]
        if isinstance(v, float) and v != v:
            if is_dev():
                warnings.warn(
                    f"Received NaN for the `{k}` attribute. If this is expected, cast the value "
                    f"to a string.\n in {tag or 'element'}",
                    UserWarning,
                    stacklevel=4,
                )
            out[k] = "NaN"
            continue
        if callable(v) and not is_event_listener_prop(k, v):
            del out[k]
            continue
        if isinstance(v, dict) and k not in (
            "style",
            "dangerouslySetInnerHTML",
            "dangerously_set_inner_html",
        ):
            out[k] = str(v)
            continue
        if isinstance(v, bool) and not is_boolean_html_attribute(k):
            del out[k]
            continue
        if is_boolean_html_attribute(k) and (v is False or v == 0 or v == ""):
            del out[k]
    tag_l = (tag or "").lower()
    for uri_key in ("href", "src"):
        if uri_key in out and out[uri_key] == "":
            if uri_key == "href" and tag_l == "a":
                continue
            del out[uri_key]
    # Drop ``None`` props so explicit null removes attributes (custom data-* etc.).
    return {k: v for k, v in out.items() if k == "children" or v is not None}


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


# Lowercase / de-underscore lookup → canonical prop keys for known DOM attributes
# (ReactDOMComponent: bad casing warnings + normalization).
_DOM_PROPERTY_ALIAS_TO_CANONICAL: dict[str, str] = {
    "size": "size",
    "maxlength": "maxLength",
    "readonly": "readOnly",
    "tabindex": "tabIndex",
    "autocomplete": "autoComplete",
    "autofocus": "autoFocus",
    "contenteditable": "contentEditable",
}


def _dom_prop_lookup_key(prop_key: str) -> str:
    return prop_key.lower().replace("_", "")


def _normalize_dom_property_key_casing_inplace(props: dict[str, Any]) -> None:
    for k in list(props.keys()):
        if k == "children":
            continue
        lk = _dom_prop_lookup_key(k)
        canon = _DOM_PROPERTY_ALIAS_TO_CANONICAL.get(lk)
        if canon is None or k == canon:
            continue
        val = props.pop(k)
        if is_dev():
            warnings.warn(
                f"Invalid DOM property {k!r}. Did you mean {canon!r}?",
                UserWarning,
                stacklevel=4,
            )
        props[canon] = val


# Minimal HTML boolean attribute set for server markup (expand with translated DOM slices).
_BOOLEAN_HTML_PROP_KEYS: frozenset[str] = frozenset(
    {
        "async",
        "autoPlay",
        "autoplay",
        "checked",
        "controls",
        "defaultChecked",
        "defer",
        "disabled",
        "hidden",
        "loop",
        "multiple",
        "muted",
        "open",
        "playsInline",
        "playsinline",
        "readOnly",
        "readonly",
        "required",
        "reversed",
        "selected",
        "scoped",
    }
)


def is_boolean_html_attribute(prop_key: str) -> bool:
    """Whether ``prop_key`` should use minimized boolean HTML form when value is True/False."""
    if prop_key in _BOOLEAN_HTML_PROP_KEYS:
        return True
    lk = prop_key.lower()
    return lk in {
        "async",
        "autoplay",
        "checked",
        "controls",
        "defer",
        "disabled",
        "hidden",
        "loop",
        "multiple",
        "muted",
        "open",
        "readonly",
        "required",
        "reversed",
        "selected",
    }
