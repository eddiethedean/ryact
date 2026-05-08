from __future__ import annotations

import warnings
from collections.abc import Mapping
from typing import Any

from ryact.dev import is_dev

from .html_props import _dom_prop_lookup_key

_DANGEROUSLY_SET_INNER_HTML_ERROR = (
    "`props.dangerouslySetInnerHTML` must be in the form `{__html: ...}`. "
    "Please visit https://react.dev/link/dangerously-set-inner-html for more information."
)

_STYLE_STRING_ERROR = (
    "The `style` prop expects a mapping from style properties to values, "
    "not a string. For example, style={{marginRight: spacing + 'em'}} "
    "when using JSX."
)


def void_element_children_or_innerhtml_error(tag: str) -> ValueError:
    """ReactDOM parity: void hosts cannot have ``children`` or ``dangerouslySetInnerHTML``."""

    return ValueError(
        f"{tag} is a void element tag and must neither have `children` nor use "
        "`dangerouslySetInnerHTML`."
    )


def _warn_and_strip_reserved_aria_dev(props: dict[str, Any], *, tag: str) -> None:
    if "aria" not in props:
        return
    if is_dev():
        warnings.warn(
            "The `aria` attribute is reserved for future use in React. "
            "Pass individual `aria-` attributes instead.\n"
            f"    in {tag}",
            UserWarning,
            stacklevel=5,
        )
    del props["aria"]


def _dangerously_set_inner_html_value_ok(v: Any) -> bool:
    return isinstance(v, dict) and set(v.keys()) == {"__html"}


def _raise_bad_dangerously_set_inner_html(props: dict[str, Any]) -> None:
    for k in ("dangerouslySetInnerHTML", "dangerously_set_inner_html"):
        if k not in props:
            continue
        if _dangerously_set_inner_html_value_ok(props[k]):
            continue
        raise ValueError(_DANGEROUSLY_SET_INNER_HTML_ERROR)


def _warn_strip_direct_inner_html_props_dev(props: dict[str, Any], *, tag: str) -> None:
    for k in list(props.keys()):
        if k == "children":
            continue
        if _dom_prop_lookup_key(str(k)) != "innerhtml":
            continue
        warnings.warn(
            "Directly setting property `innerHTML` is not permitted. "
            "For more information, lookup documentation on `dangerouslySetInnerHTML`.\n"
            f"    in {tag}",
            UserWarning,
            stacklevel=5,
        )
        del props[k]


def _warn_content_editable_and_children_dev(props: dict[str, Any], *, tag: str) -> None:
    if props.get("suppressContentEditableWarning") or props.get("suppress_content_editable_warning"):
        return
    truthy_ce = False
    for k, v in props.items():
        if k == "children":
            continue
        if _dom_prop_lookup_key(str(k)) != "contenteditable":
            continue
        if v is False or v is None:
            continue
        truthy_ce = True
        break
    if not truthy_ce:
        return
    ch = props.get("children", ())
    if len(ch) == 0:
        return
    warnings.warn(
        "A component is `contentEditable` and contains `children` managed by React. "
        "It is now your responsibility to guarantee that none of those nodes are "
        "unexpectedly modified or duplicated. This is probably not intentional.\n"
        f"    in {tag}",
        UserWarning,
        stacklevel=5,
    )


def _raise_if_style_not_mapping(props: dict[str, Any]) -> None:
    v = props.get("style")
    if v is None:
        return
    if isinstance(v, Mapping):
        return
    raise ValueError(_STYLE_STRING_ERROR)


def prepare_host_mount_props(props: Mapping[str, Any], *, tag: str) -> dict[str, Any]:
    """Host-only: ReactDOMComponent ``mountComponent`` validation (subset) before ``normalize_host_prop_dict``."""

    out = dict(props)
    _warn_and_strip_reserved_aria_dev(out, tag=tag)
    _raise_bad_dangerously_set_inner_html(out)
    if is_dev():
        _warn_strip_direct_inner_html_props_dev(out, tag=tag)
        _warn_content_editable_and_children_dev(out, tag=tag)
    _raise_if_style_not_mapping(out)
    return out
