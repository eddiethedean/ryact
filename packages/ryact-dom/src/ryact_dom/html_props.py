from __future__ import annotations

import re
import warnings
from collections.abc import Mapping
from typing import Any

from ryact.dev import is_dev

from .aria_dev import warn_invalid_aria_props_for_host_dev

# Dedupe DEV warnings that upstream asserts only once per stable prop signature.
_BOOLEAN_EMPTY_WARNED: set[tuple[str, str]] = set()


def reset_dom_warning_state() -> None:
    """Clear DEV warning dedupe state (used by translated DOM tests)."""

    _BOOLEAN_EMPTY_WARNED.clear()


# Mirrors ``shared/isAttributeNameSafe.js`` (DOM attribute names allowed for setAttribute/markup).
_ATTRIBUTE_NAME_START_CHAR = (
    r":A-Z_a-z"
    r"\u00C0-\u00D6\u00D8-\u00F6\u00F8-\u02FF\u0370-\u037D\u037F-\u1FFF"
    r"\u200C-\u200D\u2070-\u218F\u2C00-\u2FEF\u3001-\uD7FF\uF900-\uFDCF\uFDF0-\uFFFD"
)
_ATTRIBUTE_NAME_CHAR = _ATTRIBUTE_NAME_START_CHAR + r"\-.0-9\u00B7\u0300-\u036F\u203F-\u2040"
_VALID_DOM_ATTRIBUTE_NAME_RE = re.compile("^[" + _ATTRIBUTE_NAME_START_CHAR + "][" + _ATTRIBUTE_NAME_CHAR + "]*$")


def is_dom_attribute_name_safe(dom_attribute_name: str) -> bool:
    """Whether ``dom_attribute_name`` matches React's ``isAttributeNameSafe`` regex."""

    return bool(_VALID_DOM_ATTRIBUTE_NAME_RE.match(dom_attribute_name))


def warn_intrinsic_html_tag_casing_dev(tag: str, parent_host_tag: str | None) -> None:
    """DEV-only intrinsic HTML casing warning (ReactFiberConfigDOM ``default`` branch subset)."""

    if not is_dev():
        return
    if "-" in tag:
        return
    if parent_host_tag is not None and parent_host_tag.lower() == "svg":
        return
    if tag != tag.lower():
        warnings.warn(
            f"<{tag} /> is using incorrect casing. "
            "Use PascalCase for React components, "
            "or lowercase for HTML elements.\n"
            f"    in {tag}",
            UserWarning,
            stacklevel=4,
        )


# Hyphenated host tags that are not WHATWG "custom elements" (SVG/MathML integration names).
_HYPHENATED_BUILTIN_TAGS: frozenset[str] = frozenset(
    {
        "annotation-xml",
        "color-profile",
        "font-face",
        "font-face-format",
        "font-face-name",
        "font-face-src",
        "font-face-uri",
        "foreign-object",
        "glyph-ref",
        "missing-glyph",
    }
)


def _is_custom_element_dom_tag(tag: str | None) -> bool:
    """Whether ``tag`` is a custom element name (contains ``-``).

    Built-in hyphenated SVG/MathML tags are excluded.
    """
    if not tag or "-" not in tag:
        return False
    return tag.lower() not in _HYPHENATED_BUILTIN_TAGS


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
    - Boolean values on non-boolean DOM attributes are dropped on ordinary tags so they are
      not stringified as ``"True"`` / ``"False"`` (ReactDOMComponent parity). Custom elements
      (tags containing ``-``, excluding built-in hyphenated SVG/MathML names) keep unknown
      booleans: ``True`` becomes the empty-string attribute value; ``False`` omits the prop.
    - Non-listener callables on custom attributes are dropped (invalid attribute values).
    - Plain ``dict`` values (except ``style`` / ``dangerouslySetInnerHTML``) stringify like
      browser ``String(object)`` for generic custom attributes.
    - Known DOM props with bad casing (e.g. ``SiZe``) are renamed to canonical keys; DEV warns.
    - ``float('nan')`` attribute values stringify to ``\"NaN\"``; DEV warns like ReactDOM.
    - ``dangerouslySetInnerHTML`` / ``dangerously_set_inner_html`` with ``__html: None`` is
      dropped (ReactDOMComponent: allowed and treated as no inner HTML).
    - Built-in hyphenated SVG/MathML tags (``font-face``, etc.): unknown boolean props are
      dropped with a DEV warning, matching ReactDOMComponent hyphenated SVG slices.
    - Attribute keys whose serialized DOM name fails React ``isAttributeNameSafe`` are dropped
      with a DEV warning (HTML/script injection hardening).
    - ``suppressContentEditableWarning`` / ``suppress_content_editable_warning`` are consumed
      by the reconciler and omitted from DOM props.
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
    _strip_invalid_dom_attribute_names_inplace(out, tag=tag)
    for k in list(out.keys()):
        if k == "children":
            continue
        if k in ("suppressContentEditableWarning", "suppress_content_editable_warning"):
            # Consumed after this loop; do not apply unknown-attribute boolean rules.
            continue
        v = out[k]
        if k in ("dangerouslySetInnerHTML", "dangerously_set_inner_html"):
            if isinstance(v, dict) and v.get("__html") is None:
                del out[k]
            continue
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
            if _is_custom_element_dom_tag(tag):
                out[k] = v
            else:
                if is_dev():
                    t = tag or "element"
                    warnings.warn(
                        (
                            f"Invalid value for prop `{k}` on <{t}> tag. Either remove "
                            "it from the element, or pass a string or number value to "
                            "keep it in the DOM. For details, see "
                            "https://react.dev/link/attribute-behavior \n"
                            f"    in {t}"
                        ),
                        UserWarning,
                        stacklevel=4,
                    )
                del out[k]
            continue
        if isinstance(v, dict) and k not in (
            "style",
            "dangerouslySetInnerHTML",
            "dangerously_set_inner_html",
        ):
            if is_dev():
                t = tag or "element"
                warnings.warn(
                    (
                        f"Invalid value for prop `{k}` on <{t}> tag: received a mapping. "
                        "Pass a string (or use `dangerouslySetInnerHTML` for HTML).\n"
                        f"    in {t}"
                    ),
                    UserWarning,
                    stacklevel=4,
                )
            out[k] = str(v)
            continue
        if isinstance(v, bool) and not is_boolean_html_attribute(k):
            if _dom_prop_lookup_key(k) == "contenteditable":
                if v is True:
                    out[k] = True
                else:
                    del out[k]
                continue
            if _is_custom_element_dom_tag(tag):
                if v is True:
                    out[k] = ""
                else:
                    del out[k]
            else:
                tag_l_bool = (tag or "").lower()
                if is_dev() and tag_l_bool in _HYPHENATED_BUILTIN_TAGS:
                    warnings.warn(
                        (
                            f"Received `{v!r}` for a non-boolean attribute `{k!r}`. "
                            "Pass a string instead, or use undefined to omit the attribute."
                        ),
                        UserWarning,
                        stacklevel=4,
                    )
                elif is_dev() and v is True:
                    warnings.warn(
                        (
                            f"Received `True` for a non-boolean attribute `{k!r}`.\n\n"
                            "If you want to write it to the DOM, pass a string instead: "
                            f'{k}="true" or {k}={{value.toString()}}.\n'
                            f"    in {tag or 'element'}"
                        ),
                        UserWarning,
                        stacklevel=4,
                    )
                del out[k]
            continue
        if is_boolean_html_attribute(k) and (v is False or v == 0 or v == ""):
            if v == "" and is_dev():
                sig = (tag or "", k)
                if sig not in _BOOLEAN_EMPTY_WARNED:
                    warnings.warn(
                        (
                            f"Received an empty string for a boolean attribute `{k!r}`. "
                            "This will treat the attribute as if it were false. "
                            "Either pass `false` to silence this warning, or "
                            "pass `true` if you used an empty string in earlier versions of React "
                            "to indicate this attribute is true.\n"
                            f"    in {tag or 'element'}"
                        ),
                        UserWarning,
                        stacklevel=4,
                    )
                    _BOOLEAN_EMPTY_WARNED.add(sig)
            del out[k]
    out.pop("suppressContentEditableWarning", None)
    out.pop("suppress_content_editable_warning", None)

    tag_l = (tag or "").lower()
    for uri_key in ("href", "src"):
        if uri_key in out and out[uri_key] == "":
            if uri_key == "href" and tag_l == "a":
                continue
            del out[uri_key]
    _coerce_scalar_dom_attribute_values_inplace(out, tag=tag)
    warn_invalid_aria_props_for_host_dev(out, tag=tag)
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
        tail = prop[2:]
        if not tail:
            return None
        # React-style camelCase event props start with `on` followed by an uppercase letter.
        if prop[2].isupper():
            return tail.lower()
        # Custom elements can declare custom events using lowercase `on*` props, including
        # dashed event names (`onmy-event`). However, a single-letter `onx` is treated as a
        # plain attribute in our DOM parity slices.
        if len(tail) == 1:
            return None
        return tail.lower()
    return None


def is_event_listener_prop(prop: str, value: Any) -> bool:
    return callable(value) and dom_event_type_for_listener_key(prop) is not None


def html_attribute_name(prop_key: str) -> str:
    """``data_foo`` → ``data-foo``; ``aria_label`` → ``aria-label`` (Pythonic spellings)."""
    if prop_key.startswith("data_") and len(prop_key) > 5:
        return "data-" + prop_key[5:].replace("_", "-")
    if prop_key.startswith("aria_") and len(prop_key) > 5:
        return "aria-" + prop_key[5:].replace("_", "-")
    return prop_key


def _strip_invalid_dom_attribute_names_inplace(props: dict[str, Any], *, tag: str | None) -> None:
    """Drop props whose DOM attribute name fails ``isAttributeNameSafe`` (injection hardening)."""

    for k in list(props.keys()):
        if k == "children":
            continue
        if k in (
            "dangerouslySetInnerHTML",
            "dangerously_set_inner_html",
            "suppressContentEditableWarning",
            "suppress_content_editable_warning",
        ):
            continue
        dom_name = html_attribute_name(k)
        if is_dom_attribute_name_safe(dom_name):
            continue
        if is_dev():
            t = tag or "element"
            warnings.warn(
                f"Invalid attribute name: `{dom_name}`\n    in {t}",
                UserWarning,
                stacklevel=4,
            )
        del props[k]


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
    "x-height": "xHeight",
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
        "inert",
    }
)


def _coerce_scalar_dom_attribute_values_inplace(props: dict[str, Any], *, tag: str | None) -> None:
    """Coerce non-DOM-primitive attribute values that still need string conversion.

    Int/float are left intact for host props like ``meter.value``; HTML serialization
    stringifies at markup time. Unknown attributes that are plain objects are coerced
    via ``str()``; values whose ``__str__`` raises ``TypeError`` follow React's
    Temporal-like failure surface.
    """

    for k in list(props.keys()):
        if k == "children":
            continue
        v = props[k]
        if isinstance(v, (str, int, float, bool, type(None))):
            continue
        if isinstance(v, float) and v != v:
            continue
        if isinstance(v, dict):
            continue
        if callable(v):
            continue
        try:
            props[k] = str(v)
        except TypeError as e:
            if is_dev():
                warnings.warn(
                    (
                        f"The provided `{k}` attribute is an unsupported type {type(v).__name__}. "
                        "This value must be coerced to a string before using it here.\n"
                        f"    in {tag or 'element'}"
                    ),
                    UserWarning,
                    stacklevel=4,
                )
            raise TypeError(e.args[0] if e.args else "coercion failed") from e


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
        "inert",
    }
