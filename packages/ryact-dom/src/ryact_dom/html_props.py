from __future__ import annotations

import re
import warnings
from collections.abc import Mapping
from typing import Any

from ryact.dev import is_dev

from .aria_dev import warn_invalid_aria_props_for_host_dev

# Dedupe DEV warnings that upstream asserts only once per stable prop signature.
_BOOLEAN_EMPTY_WARNED: set[tuple[str, str]] = set()
_POPOVER_TARGET_NON_STRING_WARNED: set[int] = set()


def reset_dom_warning_state() -> None:
    """Clear DEV warning dedupe state (used by translated DOM tests)."""

    _BOOLEAN_EMPTY_WARNED.clear()
    _POPOVER_TARGET_NON_STRING_WARNED.clear()


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


def _is_customized_builtin_host(props: Mapping[str, Any]) -> bool:
    """Host has customized built-in ``is="..."``: ``class`` is a literal attribute (no className nudge)."""

    v = props.get("is")
    if v is None or v is False:
        return False
    if isinstance(v, str):
        return bool(v.strip())
    return True


def _merge_class_like_props_inplace(out: dict[str, Any], *, tag: str | None) -> None:
    """Merge ``class`` / ``className`` / ``claSS`` / etc. into a single ``class`` HTML attribute."""

    class_keys = [
        k
        for k in list(out.keys())
        if k != "children"
        and k != "is"
        and _dom_prop_lookup_key(str(k)) in {"class", "classname"}
    ]
    had_class_key = bool(class_keys)
    warn_rename = (
        is_dev()
        and not _is_custom_element_dom_tag(tag)
        and not _is_customized_builtin_host(out)
    )
    classes: list[Any] = []
    for key in class_keys:
        classes.append(out.pop(key))
        if warn_rename and key not in ("className", "class_name"):
            if key == "class":
                lead = "Invalid DOM property `class`. Did you mean `className`?\n"
            else:
                lead = f"Invalid DOM property `{key}`. Did you mean `className`?\n"
            warnings.warn(lead + f"    in {tag or 'element'}", UserWarning, stacklevel=4)
    if classes:
        merged = _merge_class_values(*classes)
        if merged:
            out["class"] = merged
        elif had_class_key:
            out["class"] = ""


def _normalize_arabic_form_hyphen_alias_inplace(props: dict[str, Any], *, tag: str | None) -> None:
    if "arabic-form" not in props:
        return
    if is_dev():
        warnings.warn(
            "Invalid DOM property `arabic-form`. Did you mean `arabicForm`?\n"
            f"    in {tag or 'element'}",
            UserWarning,
            stacklevel=4,
        )
    props["arabicForm"] = props.pop("arabic-form")


def _warn_and_strip_unsupported_focus_in_out_props_inplace(props: dict[str, Any], *, tag: str | None) -> None:
    """Remove ``onFocusIn`` / ``onFocusOut`` spellings; DEV-nudge per ReactDOM (nesting validation)."""

    t = tag or "element"
    for k in list(props.keys()):
        if k == "children":
            continue
        lk = str(k).lower().replace("_", "")
        if lk not in ("onfocusin", "onfocusout"):
            continue
        if is_dev():
            warnings.warn(
                (
                    "React uses onFocus and onBlur instead of onFocusIn and onFocusOut. "
                    "All React events are normalized to bubble, so onFocusIn and onFocusOut "
                    f"are not needed/supported by React.\n    in {t}"
                ),
                UserWarning,
                stacklevel=4,
            )
        del props[k]


def _input_defaultvalue_fixup(props: dict[str, Any]) -> None:
    """ReactDOMInput: drop stray ``defaultValue`` when ``value`` is set; else map it to ``value``."""

    if "value" in props:
        props.pop("defaultValue", None)
        props.pop("default_value", None)
        return
    for dk in ("defaultValue", "default_value"):
        if dk not in props:
            continue
        props["value"] = props.pop(dk)
        return


def _reorder_input_props_inplace(props: dict[str, Any]) -> None:
    """ReactDOMInput mount order: ``min`` / ``max`` / ``step`` / ``type`` before ``value`` / ``defaultValue``."""

    ch = props.pop("children", None)
    work = [(k, props[k]) for k in props]
    props.clear()
    ordered: list[tuple[str, Any]] = []
    for lk_need in ("min", "max", "step", "type"):
        nxt: list[tuple[str, Any]] = []
        picked: tuple[str, Any] | None = None
        for k, v in work:
            if picked is None and _dom_prop_lookup_key(k) == lk_need:
                picked = (k, v)
            else:
                nxt.append((k, v))
        if picked is not None:
            ordered.append(picked)
        work = nxt
    head: list[tuple[str, Any]] = []
    tail: list[tuple[str, Any]] = []
    for k, v in work:
        if _dom_prop_lookup_key(k) in ("value", "defaultvalue"):
            tail.append((k, v))
        else:
            head.append((k, v))
    tail.sort(key=lambda kv: (0 if _dom_prop_lookup_key(kv[0]) == "value" else 1, kv[0]))
    for k, v in ordered + head + tail:
        props[k] = v
    if ch is not None:
        props["children"] = ch


def normalize_host_prop_dict(
    props: Mapping[str, Any],
    *,
    tag: str | None = None,
    is_ssr: bool = False,
) -> dict[str, Any]:
    """
    Normalize React- and Python-style host props to a single DOM-facing shape.

    Parameters
    ----------
    is_ssr
        When True (server render), mis-cased ``onKeydown`` is renamed without a DEV warning; other
        bad ``on*`` casing uses the generic SSR handler message (ReactDOM parity).

    - ``class`` / odd-cased ``claSS`` / ``class_name`` merge into HTML ``class``; on ordinary
      elements DEV warns to use ``className`` (ReactDOM ``Attributes with aliases``); customized
      built-in hosts (``is="..."``) and native custom tags skip the nudge; ``arabic-form`` renames
      to ``arabicForm`` with a DEV warning (SVG).
    - Explicit ``None`` / empty clears to ``class=""`` when any class key was present
      (matches DOMPropertyOperations: empty string instead of omitting the attribute).
    - Empty ``href`` is omitted for most tags, but preserved for ``<a>`` (updateDOM empty
      href on anchors) when ``tag`` is ``"a"``. Empty ``src`` is still omitted.
    - Boolean values on non-boolean DOM attributes are dropped on ordinary tags so they are
      not stringified as ``"True"`` / ``"False"`` (ReactDOMComponent parity), except ``value`` /
      ``defaultValue`` on ``<input>`` / ``<textarea>`` which stringify to ``\"true\"`` /
      ``\"false\"`` (ReactDOMInput). On **custom**
      elements, unknown non-boolean props keep real Python ``bool`` values (React assigns to
      the underlying DOM property); SSR mirrors this with an empty-string attribute for ``True``.
    - ``spellCheck`` (and pythonic ``spell_check``): boolean props stringify to the DOM
      enumerated spellcheck values ``\"true\"`` / ``\"false\"`` (React ``String boolean attributes``).
    - String literals ``\"true\"`` / ``\"false\"`` on minimized boolean HTML attributes (e.g. ``hidden``)
      emit DEV warnings and coerce to boolean presence (same as ``hidden={true}``); this matches
      ReactDOM ambiguous-string parity because the browser treats any ``hidden`` value as truthy.
    - Non-listener callables on custom attributes are dropped (invalid attribute values).
    - Plain ``dict`` values used as non-``style`` / non-innerHTML attributes stringify to
      ``[object Object]`` (React ``Object.prototype.toString`` / DOMPropertyOperations parity).
    - Known DOM props with bad casing (e.g. ``SiZe``) are renamed to canonical keys; DEV warns.
    - Bad ``on*`` event prop casing is renamed: client suggests ``onInput`` / ``onKeyDown``; SSR uses a
      generic camelCase / ``onClick`` nudge and does not warn for ``onKeydown`` (ReactDOM parity).
    - ``onFocusIn`` / ``onFocusOut`` (any casing, including ``on_focus_in``) are stripped with a DEV
      nudge to use ``onFocus`` / ``onBlur`` (ReactDOM nesting validation).
    - ``float('nan')`` attribute values stringify to ``\"NaN\"``; DEV warns like ReactDOM.
    - ``dangerouslySetInnerHTML`` / ``dangerously_set_inner_html`` with ``__html: None`` is
      dropped (ReactDOMComponent: allowed and treated as no inner HTML).
    - Built-in hyphenated SVG/MathML tags (``font-face``, etc.): unknown boolean props are
      dropped with a DEV warning, matching ReactDOMComponent hyphenated SVG slices.
    - Attribute keys whose serialized DOM name fails React ``isAttributeNameSafe`` are dropped
      with a DEV warning (HTML/script injection hardening).
    - ``suppressContentEditableWarning`` / ``suppress_content_editable_warning`` are consumed
      by the reconciler and omitted from DOM props.
    - ``<input>`` (only): uncontrolled ``defaultValue`` / ``default_value`` is renamed to ``value``
      so markup matches the DOM ``value`` attribute (ReactDOMInput). Host prop order is normalized
      to ``min``, ``max``, ``step``, ``type``, then other props, then ``value`` / ``defaultValue``,
      matching React's update pipeline for range inputs and ``value`` before ``type`` edge cases.
    - ``<input>`` with ``value={null}`` / ``value=None``: DEV warns like ReactDOM; the ``value``
      entry is then omitted from normalized props (reset/submit keep their default label behavior).
    """
    out = dict(props)
    _merge_class_like_props_inplace(out, tag=tag)
    _normalize_arabic_form_hyphen_alias_inplace(out, tag=tag)
    _warn_and_strip_unsupported_focus_in_out_props_inplace(out, tag=tag)
    _normalize_event_handler_prop_casing_inplace(out, tag=tag, is_ssr=is_ssr)
    _normalize_dom_property_key_casing_inplace(out, tag=tag)
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
            # ReactDOM: plain objects use ``Object.prototype.toString`` → ``[object Object]``.
            out[k] = "[object Object]"
            continue
        if _dom_prop_lookup_key(k) == "popovertarget" and v is not None and not isinstance(v, (str, int, float, bool)):
            if is_dev():
                wid = id(v)
                if wid not in _POPOVER_TARGET_NON_STRING_WARNED:
                    t = tag or "element"
                    warnings.warn(
                        (
                            "The `popoverTarget` prop expects the ID of an Element as a string. "
                            f"Received {type(v).__name__} instead.\n"
                            f"    in {t}"
                        ),
                        UserWarning,
                        stacklevel=4,
                    )
                    _POPOVER_TARGET_NON_STRING_WARNED.add(wid)
            del out[k]
            continue
        if is_boolean_html_attribute(k) and isinstance(v, str) and _dom_prop_lookup_key(v) == _dom_prop_lookup_key(k):
            # Legacy HTML expansions: ``disabled="disabled"``, ``checked="checked"``, ``readonly="readonly"``, …
            out[k] = True
            continue
        if _dom_prop_lookup_key(k) in _STRING_BOOLEAN_DOM_LOOKUP_KEYS and isinstance(v, bool):
            out[k] = "true" if v else "false"
            continue
        if is_boolean_html_attribute(k) and isinstance(v, str) and v in ("true", "false"):
            if is_dev():
                t = tag or "element"
                if v == "false":
                    warnings.warn(
                        (
                            f"Received the string `false` for the boolean attribute `{k}`. "
                            "The browser will interpret it as a truthy value. "
                            f"Did you mean {k}={{false}}?\n"
                            f"    in {t}"
                        ),
                        UserWarning,
                        stacklevel=4,
                    )
                else:
                    warnings.warn(
                        (
                            f"Received the string `true` for the boolean attribute `{k}`. "
                            'Although this works, it will not work as expected if you pass the string "false". '
                            f"Did you mean {k}={{true}}?\n"
                            f"    in {t}"
                        ),
                        UserWarning,
                        stacklevel=4,
                    )
            out[k] = True
            continue
        tag_l_form = (tag or "").lower()
        lk_form = _dom_prop_lookup_key(k)
        if (
            tag_l_form in ("input", "textarea")
            and lk_form in ("value", "defaultvalue")
            and isinstance(v, bool)
        ):
            # ReactDOMInput: ``value={true}`` / ``value={false}`` stringify like ``toString`` on the host.
            out[k] = "true" if v else "false"
            continue
        if isinstance(v, bool) and not is_boolean_html_attribute(k):
            if _dom_prop_lookup_key(k) == "contenteditable":
                if v is True:
                    out[k] = True
                else:
                    del out[k]
                continue
            if _is_custom_element_dom_tag(tag):
                out[k] = v
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

    if (tag or "").lower() == "input":
        _input_defaultvalue_fixup(out)
        _reorder_input_props_inplace(out)

    tag_l = (tag or "").lower()
    for uri_key in ("href", "src"):
        if uri_key in out and out[uri_key] == "":
            if uri_key == "href" and tag_l == "a":
                continue
            del out[uri_key]
    _coerce_scalar_dom_attribute_values_inplace(out, tag=tag)
    warn_invalid_aria_props_for_host_dev(out, tag=tag)
    if (tag or "").lower() == "input" and is_dev() and "value" in out and out["value"] is None:
        warnings.warn(
            "`value` prop on `input` should not be null. "
            "Consider using an empty string to clear the component "
            "or `undefined` for uncontrolled components.\n"
            "    in input",
            UserWarning,
            stacklevel=4,
        )
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
    lk = _dom_prop_lookup_key(prop_key)
    if lk == "htmlfor":
        return "for"
    if lk == "autofocus":
        return "autofocus"
    if lk == "spellcheck":
        return "spellcheck"
    if lk == "acceptcharset":
        return "accept-charset"
    if lk == "arabicform":
        return "arabic-form"
    if lk == "xlinkhref":
        return "xlink:href"
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
    "spellcheck": "spellCheck",
    "acceptcharset": "acceptCharset",
    "readonly": "readOnly",
    "for": "htmlFor",
    "tabindex": "tabIndex",
    "autocomplete": "autoComplete",
    "autofocus": "autoFocus",
    "contenteditable": "contentEditable",
    "credentialless": "credentialless",
    "x-height": "xHeight",
}

_STRING_BOOLEAN_DOM_LOOKUP_KEYS: frozenset[str] = frozenset({"spellcheck"})


def _dom_prop_lookup_key(prop_key: str) -> str:
    return prop_key.lower().replace("_", "")


def _canonical_react_event_prop_name(prop: str) -> str | None:
    """If ``prop`` looks like an ``on*`` listener with invalid React casing, return the canonical key."""

    if not isinstance(prop, str) or not prop.startswith("on") or prop.startswith("on_"):
        return None
    if len(prop) <= 3:
        return None
    lk = _dom_prop_lookup_key(prop)
    if lk == "onkeydown" and prop != "onKeyDown":
        return "onKeyDown"
    if prop[2].islower() and dom_event_type_for_listener_key(prop) is not None:
        return "on" + prop[2].upper() + prop[3:]
    return None


def _normalize_event_handler_prop_casing_inplace(
    props: dict[str, Any], *, tag: str | None, is_ssr: bool
) -> None:
    if _is_custom_element_dom_tag(tag):
        return
    t = tag or "element"
    for k in list(props.keys()):
        if k == "children":
            continue
        canon = _canonical_react_event_prop_name(k)
        if canon is None or k == canon:
            continue
        val = props.pop(k)
        if is_dev():
            lk = _dom_prop_lookup_key(k)
            if is_ssr and lk == "onkeydown" and k != "onKeyDown":
                pass
            elif is_ssr:
                warnings.warn(
                    (
                        f"Invalid event handler property `{k}`. "
                        "React events use the camelCase naming convention, "
                        "for example `onClick`.\n"
                        f"    in {t}"
                    ),
                    UserWarning,
                    stacklevel=4,
                )
            else:
                warnings.warn(
                    (
                        f"Invalid event handler property `{k}`. Did you mean `{canon}`?\n"
                        f"    in {t}"
                    ),
                    UserWarning,
                    stacklevel=4,
                )
        props[canon] = val


def _normalize_dom_property_key_casing_inplace(props: dict[str, Any], *, tag: str | None = None) -> None:
    t = tag or "element"
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
                f"Invalid DOM property `{k}`. Did you mean `{canon}`?\n    in {t}",
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
        "autoFocus",
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
        "allowFullScreen",
        "allowfullscreen",
        "credentialless",
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

    tag_l = (tag or "").lower()
    for k in list(props.keys()):
        if k == "children":
            continue
        if tag_l == "select" and k in ("value", "defaultValue", "default_value"):
            continue
        if tag_l == "option" and k == "value":
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
        "autofocus",
        "checked",
        "controls",
        "defer",
        "disabled",
        "hidden",
        "loop",
        "multiple",
        "muted",
        "open",
        "allowfullscreen",
        "readonly",
        "required",
        "reversed",
        "selected",
        "inert",
    }
